"""Chart regression tests. Requires Helm 3 and PyYAML; no cluster required."""

import subprocess
import tempfile
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
COMPONENTS = (
    "gwagent",
    "ingress-dataplane",
    "ingress",
    "nocturne",
    "octovigil",
    "rscserver",
)


def base_values(component):
    if component == "rscserver":
        return yaml.safe_load((ROOT / "examples/rscserver.yaml").read_text())

    return {}


def helm(component, values=None, command="template", succeeds=True):
    chart = ROOT / "charts" / f"octelium-{component}"
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml") as values_file:
        yaml.safe_dump(
            values if values is not None else base_values(component), values_file
        )
        values_file.flush()
        args = ["helm", command]
        if command == "template":
            args += ["test"]
        args += [str(chart), "--namespace", "octelium", "-f", values_file.name]
        if command == "lint":
            args += ["--strict"]
        result = subprocess.run(args, text=True, capture_output=True)
    if succeeds and result.returncode:
        raise AssertionError(result.stderr + result.stdout)
    if not succeeds:
        if not result.returncode:
            raise AssertionError("Expected Helm to reject these values")
        return result.stderr + result.stdout
    if command == "lint":
        return result.stdout
    return [item for item in yaml.safe_load_all(result.stdout) if item]


def pod_spec(docs):
    return next(
        d["spec"]["template"]["spec"]
        for d in docs
        if d["kind"] in ("Deployment", "DaemonSet")
    )


class ChartsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        for component in COMPONENTS:
            subprocess.run(
                [
                    "helm",
                    "dependency",
                    "build",
                    "--skip-refresh",
                    str(ROOT / "charts" / f"octelium-{component}"),
                ],
                check=True,
                capture_output=True,
            )

    def test_custom_labels_preserve_selectors(self):
        for component in COMPONENTS:
            with self.subTest(component=component):
                values = base_values(component)
                values["podLabels"] = {
                    "example.com/team": "platform",
                    "app": "conflicting",
                    "octelium.com/component": "conflicting",
                }
                if component == "ingress-dataplane":
                    values["service"] = {
                        "labels": {
                            "example.com/exposure": "public",
                            "app": "conflicting",
                        }
                    }
                docs = helm(component, values)
                workload = next(
                    d for d in docs if d["kind"] in ("Deployment", "DaemonSet")
                )
                labels = workload["spec"]["template"]["metadata"]["labels"]
                self.assertEqual(labels["example.com/team"], "platform")
                self.assertNotIn("example.com/team", workload["metadata"]["labels"])
                self.assertEqual(labels["app"], "octelium")
                for key, value in workload["spec"]["selector"]["matchLabels"].items():
                    self.assertEqual(labels[key], value)
                for service in (d for d in docs if d["kind"] == "Service"):
                    for key, value in service["spec"].get("selector", {}).items():
                        self.assertEqual(labels[key], value)
                if component == "ingress-dataplane":
                    service = next(d for d in docs if d["kind"] == "Service")
                    self.assertEqual(
                        service["metadata"]["labels"]["example.com/exposure"], "public"
                    )
                    self.assertEqual(service["metadata"]["labels"]["app"], "octelium")
                    self.assertNotIn("example.com/exposure", labels)
                values["podLabels"] = {"invalid": 123}
                helm(component, values, succeeds=False)
        helm(
            "ingress-dataplane",
            {"service": {"labels": {"invalid": 123}}},
            succeeds=False,
        )

    def test_storage_secret_references(self):
        values = base_values("rscserver")
        for storage in ("postgresql", "redis"):
            values[storage]["secretRef"] = {
                "name": storage + "-credentials",
                "usernameKey": "custom-user",
                "passwordKey": "custom-password",
            }
        pod = pod_spec(helm("rscserver", values))
        for container in [pod["containers"][0], pod["initContainers"][0]]:
            env = {entry["name"]: entry for entry in container["env"]}
            for storage, prefix in (("postgresql", "POSTGRES"), ("redis", "REDIS")):
                for suffix, key in (
                    ("USERNAME", "custom-user"),
                    ("PASSWORD", "custom-password"),
                ):
                    self.assertEqual(
                        env[f"OCTELIUM_{prefix}_{suffix}"],
                        {
                            "name": f"OCTELIUM_{prefix}_{suffix}",
                            "valueFrom": {
                                "secretKeyRef": {
                                    "name": storage + "-credentials",
                                    "key": key,
                                }
                            },
                        },
                    )
        for storage in ("postgresql", "redis"):
            for key in ("name", "usernameKey", "passwordKey"):
                invalid = base_values("rscserver")
                invalid[storage]["secretRef"][key] = ""
                helm("rscserver", invalid, succeeds=False)
            for old_key in ("username", "existingSecret", "passwordKey"):
                invalid = base_values("rscserver")
                invalid[storage][old_key] = "old-setting"
                helm("rscserver", invalid, succeeds=False)

    def test_initializer_image_defaults_to_app_version(self):
        metadata = yaml.safe_load(
            (ROOT / "charts/octelium-rscserver/Chart.yaml").read_text()
        )
        values = base_values("rscserver")
        init = pod_spec(helm("rscserver", values))["initContainers"][0]
        self.assertEqual(
            init["image"],
            "ghcr.io/wyndure/octelium-initializer:" + metadata["appVersion"],
        )
        values["initializer"] = {"image": {"tag": "custom-build"}}
        init = pod_spec(helm("rscserver", values))["initContainers"][0]
        self.assertEqual(
            init["image"], "ghcr.io/wyndure/octelium-initializer:custom-build"
        )

    def test_nocturne_rbac(self):
        docs = helm("nocturne")
        cluster = next(d for d in docs if d["kind"] == "ClusterRole")
        role = next(d for d in docs if d["kind"] == "Role")

        def grants(obj):
            return {
                (group, resource, verb)
                for rule in obj["rules"]
                for group in rule["apiGroups"]
                for resource in rule["resources"]
                for verb in rule["verbs"]
            }

        expected_cluster = {
            ("", r, v)
            for r in ("pods", "services", "secrets", "nodes")
            for v in ("get", "list", "watch")
        }
        expected_cluster.add(("", "nodes", "update"))
        self.assertEqual(grants(cluster), expected_cluster)
        expected_workload = {
            ("apps", "deployments", v)
            for v in ("get", "list", "create", "update", "delete")
        }
        expected_workload |= {
            ("", r, v)
            for r in ("services", "secrets")
            for v in ("create", "update", "delete")
        }
        expected_workload |= {
            ("", "configmaps", v) for v in ("get", "create", "update", "delete")
        }
        self.assertEqual(grants(role), expected_workload)
        self.assertEqual(role["metadata"]["namespace"], "octelium")
        binding = next(d for d in docs if d["kind"] == "RoleBinding")
        self.assertEqual(binding["metadata"]["namespace"], "octelium")
        self.assertEqual(binding["roleRef"]["kind"], "Role")
        self.assertEqual(binding["roleRef"]["name"], role["metadata"]["name"])
        self.assertEqual(
            binding["subjects"],
            [
                {
                    "kind": "ServiceAccount",
                    "name": "octelium-nocturne",
                    "namespace": "octelium",
                }
            ],
        )
        cluster_binding = next(d for d in docs if d["kind"] == "ClusterRoleBinding")
        self.assertEqual(
            cluster_binding["roleRef"]["name"], cluster["metadata"]["name"]
        )
        disabled = helm("nocturne", {"rbac": {"create": False}})
        self.assertFalse(
            any(
                d["kind"]
                in (
                    "ServiceAccount",
                    "ClusterRole",
                    "ClusterRoleBinding",
                    "Role",
                    "RoleBinding",
                )
                for d in disabled
            )
        )
        # A different deployment namespace must not grant workload writes there.
        chart = ROOT / "charts/octelium-nocturne"
        rendered = subprocess.run(
            ["helm", "template", "test", str(chart), "-n", "control-plane"],
            text=True,
            capture_output=True,
            check=True,
        )
        docs = [d for d in yaml.safe_load_all(rendered.stdout) if d]
        binding = next(d for d in docs if d["kind"] == "RoleBinding")
        self.assertEqual(binding["metadata"]["namespace"], "octelium")
        self.assertEqual(binding["subjects"][0]["namespace"], "control-plane")

    def test_region_ref(self):
        for component in COMPONENTS:
            if component == "ingress-dataplane":
                helm(component, {"regionRef": {"name": "region"}}, succeeds=False)
                continue
            v = base_values(component)
            v["regionRef"] = {"name": "selected-region"}
            env = {
                e["name"]: e
                for e in pod_spec(helm(component, v))["containers"][0]["env"]
            }
            self.assertEqual(
                env["OCTELIUM_REGION_NAME"],
                {
                    "name": "OCTELIUM_REGION_NAME",
                    "valueFrom": {
                        "configMapKeyRef": {"name": "selected-region", "key": "name"}
                    },
                },
            )
            if component == "nocturne":
                self.assertEqual(
                    env["OCTELIUM_REGION_UID"],
                    {
                        "name": "OCTELIUM_REGION_UID",
                        "valueFrom": {
                            "configMapKeyRef": {"name": "selected-region", "key": "uid"}
                        },
                    },
                )
            for bad in (
                {"region": {"name": "old", "uid": "old"}},
                {"regionRef": {"name": ""}},
                {"regionRef": {"name": "region", "namespace": "other"}},
                {"regionRef": {"name": "region", "key": "other"}},
            ):
                invalid = dict(v, **bad)
                helm(component, invalid, succeeds=False)

    def test_cluster_config_map(self):
        values = base_values("rscserver")
        values["clusterConfigMap"] = {"name": "cluster-info"}
        docs = helm("rscserver", values)
        pod = next(d for d in docs if d["kind"] == "Deployment")["spec"]["template"][
            "spec"
        ]
        self.assertFalse(pod["automountServiceAccountToken"])
        self.assertEqual(pod["serviceAccountName"], "octelium-rscserver-initializer")
        env = {e["name"]: e for e in pod["initContainers"][0]["env"]}
        self.assertEqual(
            env["OCTELIUM_INITIALIZER_CLUSTER_CONFIG_MAP"]["value"], "cluster-info"
        )
        self.assertNotIn("OCTELIUM_INITIALIZER_CLUSTER_CONFIG_MAP_KEY", env)
        invalid = dict(
            values, clusterConfigMap={"name": "cluster-info", "key": "custom"}
        )
        helm("rscserver", invalid, succeeds=False)
        self.assertEqual(
            pod["initContainers"][0]["volumeMounts"][0]["name"],
            "initializer-api-access",
        )
        self.assertNotIn(
            "initializer-api-access",
            [m["name"] for m in pod["containers"][0].get("volumeMounts", [])],
        )
        rule = next(d for d in docs if d["kind"] == "Role")["rules"][0]
        self.assertEqual(rule["verbs"], ["patch"])
        self.assertEqual(rule["resourceNames"], ["cluster-info"])
        self.assertTrue(
            any(
                d["kind"] == "ConfigMap" and d["metadata"]["name"] == "cluster-info"
                for d in docs
            )
        )

    def test_initializer_storage_and_isolation(self):
        values = base_values("rscserver")
        values["extraEnv"] = [
            {
                "name": "OCTELIUM_POSTGRES_HOST",
                "valueFrom": {"secretKeyRef": {"name": "override", "key": "host"}},
            },
            {"name": "OCTELIUM_REDIS_USERNAME", "value": "application"},
            {"name": "SERVER_ONLY", "value": "private"},
        ]
        values["extraEnvFrom"] = [{"configMapRef": {"name": "storage-options"}}]
        values["spiffe"] = {"enabled": True, "trustDomain": "example.org"}
        values["initializer"] = {
            "timeout": "45s",
            "image": {
                "repository": "registry.example.com/initializer",
                "digest": "sha256:" + "b" * 64,
            },
            "extraEnv": [
                {
                    "name": "OCTELIUM_CLUSTER_DOMAIN",
                    "valueFrom": {"secretKeyRef": {"name": "domain", "key": "value"}},
                }
            ],
            "extraEnvFrom": [{"secretRef": {"name": "initializer-options"}}],
            "extraVolumeMounts": [{"name": "scratch", "mountPath": "/scratch"}],
        }
        values["extraVolumes"] = [{"name": "scratch", "emptyDir": {}}]
        pod = pod_spec(helm("rscserver", values))
        init = pod["initContainers"][-1]
        env = {entry["name"]: entry for entry in init["env"]}
        main_env = {entry["name"]: entry for entry in pod["containers"][0]["env"]}
        for name, entry in main_env.items():
            if name.startswith(("OCTELIUM_POSTGRES_", "OCTELIUM_REDIS_")):
                self.assertEqual(env[name], entry)
        self.assertNotIn("OCTELIUM_REGION_NAME", env)
        self.assertNotIn("OCTELIUM_ENABLE_SPIFFE_CSI", env)
        self.assertNotIn("SERVER_ONLY", env)
        self.assertEqual(
            env["OCTELIUM_CLUSTER_DOMAIN"], values["initializer"]["extraEnv"][0]
        )
        self.assertEqual(
            init["envFrom"],
            values["extraEnvFrom"] + values["initializer"]["extraEnvFrom"],
        )
        self.assertEqual(
            init["volumeMounts"], values["initializer"]["extraVolumeMounts"]
        )
        self.assertEqual(init["args"], ["--timeout=45s"])
        self.assertEqual(
            init["image"], "registry.example.com/initializer@sha256:" + "b" * 64
        )
        self.assertEqual(init["securityContext"]["runAsUser"], 65532)
        self.assertTrue(init["securityContext"]["readOnlyRootFilesystem"])
        self.assertEqual(pod["serviceAccountName"], "default")
        self.assertFalse(pod["automountServiceAccountToken"])

    def test_initializer_disabled(self):
        values = base_values("rscserver")
        values["initializer"] = {"enabled": False}
        docs = helm("rscserver", values)
        self.assertNotIn("initContainers", pod_spec(docs))
        self.assertEqual(pod_spec(docs)["serviceAccountName"], "default")
        self.assertFalse(
            any(
                d["kind"] in ("ConfigMap", "Role", "RoleBinding", "ServiceAccount")
                for d in docs
            )
        )
        values["clusterConfigMap"] = {"name": "cluster-info"}
        helm("rscserver", values, succeeds=False)

    def test_initializer_rejects_conflicting_settings(self):
        for invalid in [
            {"initializer": {"enabled": "yes"}},
            {"initializer": {"timeout": "0s"}},
            {"initializer": {"timeout": "0h0m0s"}},
            {"initializer": {"timeout": "tomorrow"}},
            {
                "initializer": {
                    "extraEnv": [{"name": "POD_NAMESPACE", "value": "other"}]
                }
            },
            {"initializer": {"extraEnv": [{"name": "X"}, {"name": "X"}]}},
            {
                "extraInitContainers": [
                    {"name": "octelium-initializer", "image": "custom"}
                ]
            },
            {"clusterConfigMap": {"name": "octelium-region"}},
            {
                "clusterConfigMap": {"name": "cluster-info"},
                "extraVolumes": [{"name": "initializer-api-access", "emptyDir": {}}],
            },
        ]:
            with self.subTest(invalid=invalid):
                values = base_values("rscserver")
                values.update(invalid)
                helm("rscserver", values, succeeds=False)

    def test_defaults_and_lint(self):
        for component in COMPONENTS:
            with self.subTest(component=component):
                helm(component, command="lint")
                spec = pod_spec(helm(component))
                main = spec["containers"][0]
                self.assertFalse(main["securityContext"]["allowPrivilegeEscalation"])
                if component == "rscserver":
                    self.assertEqual(
                        [c["name"] for c in spec["initContainers"]],
                        ["octelium-initializer"],
                    )
                else:
                    self.assertNotIn("initContainers", spec)
                self.assertNotIn("envFrom", main)
                if component not in ("gwagent", "ingress-dataplane"):
                    self.assertEqual(main["readinessProbe"]["grpc"]["port"], 49090)
                env = {v["name"]: v for v in main.get("env", [])}
                if component != "nocturne":
                    self.assertNotIn("OCTELIUM_REGION_UID", env)
                if component == "ingress-dataplane":
                    self.assertFalse(env)
                elif component == "rscserver":
                    self.assertEqual(env["OCTELIUM_POSTGRES_NOSSL"]["value"], "false")
                    self.assertEqual(env["OCTELIUM_REDIS_USE_TLS"]["value"], "true")

    def test_extensions_with_and_without_spiffe(self):
        for component in COMPONENTS:
            for spiffe in (False, True):
                with self.subTest(component=component, spiffe=spiffe):
                    v = base_values(component)
                    v.update(
                        {
                            "podSecurityContext": {"fsGroup": 12345},
                            "securityContext": {
                                "runAsUser": 12345,
                                "seccompProfile": {"type": "RuntimeDefault"},
                            },
                            "extraVolumes": [{"name": "scratch", "emptyDir": {}}],
                            "extraVolumeMounts": [
                                {"name": "scratch", "mountPath": "/scratch"}
                            ],
                            "extraInitContainers": [
                                {
                                    "name": "prepare",
                                    "image": "busybox:1.37.0",
                                    "command": [
                                        "sh",
                                        "-c",
                                        "echo ready > /scratch/ready",
                                    ],
                                    "volumeMounts": [
                                        {"name": "scratch", "mountPath": "/scratch"}
                                    ],
                                }
                            ],
                            "extraEnv": [
                                {"name": "TEST_VALUE", "value": "hello"},
                                {
                                    "name": "OCTELIUM_REGION_NAME",
                                    "valueFrom": {
                                        "fieldRef": {"fieldPath": "metadata.namespace"}
                                    },
                                },
                            ],
                            "extraEnvFrom": [
                                {"configMapRef": {"name": "test-env"}},
                                {"secretRef": {"name": "test-secret"}},
                            ],
                            "spiffe": {
                                "enabled": spiffe,
                                "socketPath": "/run/spire/sockets/agent.sock",
                            },
                        }
                    )
                    spec = pod_spec(helm(component, v))
                    main = spec["containers"][0]
                    self.assertEqual(spec["securityContext"]["fsGroup"], 12345)
                    self.assertEqual(main["securityContext"]["runAsUser"], 12345)
                    self.assertEqual(
                        main["securityContext"]["seccompProfile"]["type"],
                        "RuntimeDefault",
                    )
                    self.assertFalse(
                        main["securityContext"]["allowPrivilegeEscalation"]
                    )
                    if component == "rscserver":
                        self.assertEqual(
                            spec["initContainers"][:-1], v["extraInitContainers"]
                        )
                        self.assertEqual(
                            spec["initContainers"][-1]["name"], "octelium-initializer"
                        )
                    else:
                        self.assertEqual(
                            spec["initContainers"], v["extraInitContainers"]
                        )
                    names = {x["name"] for x in spec["volumes"]}
                    mounts = {x["name"] for x in main["volumeMounts"]}
                    self.assertIn("scratch", names & mounts)
                    self.assertEqual("spiffe-agent" in names & mounts, spiffe)
                    if component == "gwagent":
                        self.assertIn("multus-conf", names & mounts)
                    if component == "ingress-dataplane":
                        self.assertIn("envoy-config", names & mounts)
                    env = main["env"]
                    self.assertEqual(len(env), len({x["name"] for x in env}))
                    region = next(x for x in env if x["name"] == "OCTELIUM_REGION_NAME")
                    self.assertEqual(region, v["extraEnv"][1])
                    self.assertEqual(main["envFrom"], v["extraEnvFrom"])

    def test_schema_rejects_invalid_extensions_and_old_fields(self):
        for component in COMPONENTS:
            for bad in (
                {"image": {"registry": "example.org"}},
                {"extraEnv": [{"name": "X", "value": 123}]},
                {"extraEnv": [{"name": "X", "value": "x", "valueFrom": {}}]},
                {"extraInitContainers": [{"name": "missing-image"}]},
                {"extraVolumeMounts": [{"name": "missing-path"}]},
                {"extraEnvFrom": [{}]},
                {"extraEnv": [{"name": "X"}, {"name": "X"}]},
            ):
                with self.subTest(component=component, bad=bad):
                    values = base_values(component)
                    values.update(bad)
                    helm(component, values, succeeds=False)
        for component, old in [
            ("gwagent", {"multusConfDir": "/old"}),
            ("ingress", {"ingress": {"frontProxy": True}}),
            ("ingress-dataplane", {"region": {"name": "unused"}}),
            ("nocturne", {"domain": "old.example"}),
            ("rscserver", {"networkPolicy": {"enabled": True}}),
        ]:
            v = base_values(component)
            v.update(old)
            helm(component, v, succeeds=False)

    def test_dependency_requirements(self):
        helm("nocturne", {"regionRef": {"name": ""}}, succeeds=False)
        helm("nocturne", {"replicas": 2}, succeeds=False)
        helm("rscserver", {}, succeeds=False)

    def test_image_digest(self):
        for component in COMPONENTS:
            v = base_values(component)
            v["image"] = {
                "repository": "registry.example/component",
                "digest": "sha256:" + "a" * 64,
                "tag": "ignored",
            }
            self.assertEqual(
                pod_spec(helm(component, v))["containers"][0]["image"],
                "registry.example/component@sha256:" + "a" * 64,
            )

    def test_discovery_alias_variants(self):
        for component in ("gwagent", "ingress", "nocturne", "octovigil"):
            for host, headless, port in [
                ("backend.example", True, 8080),
                ("192.0.2.10", True, 8080),
                ("2001:db8::10", True, 8080),
                ("192.0.2.10", False, 9090),
            ]:
                with self.subTest(component=component, host=host, headless=headless):
                    v = base_values(component)
                    v["resourceServer"] = {
                        "endpoint": host,
                        "headless": headless,
                        "port": port,
                    }
                    docs = helm(component, v)
                    alias = next(
                        d
                        for d in docs
                        if d["kind"] == "Service"
                        and d["metadata"]["name"] == "octelium-rscserver"
                    )
                    self.assertEqual(alias["spec"]["ports"][0]["port"], 8080)
                    slices = [d for d in docs if d["kind"] == "EndpointSlice"]
                    if host == "backend.example":
                        self.assertEqual(alias["spec"]["externalName"], host)
                        self.assertFalse(slices)
                    else:
                        self.assertEqual(slices[0]["endpoints"][0]["addresses"], [host])
                        self.assertEqual(slices[0]["ports"][0]["port"], port)
                        self.assertEqual(
                            alias["spec"].get("clusterIP") == "None", headless
                        )
            for endpoint, port in [
                ("octelium-rscserver.octelium.svc", 8080),
                ("backend.example", 9090),
            ]:
                v = base_values(component)
                v["resourceServer"] = {"endpoint": endpoint, "port": port}
                helm(component, v, succeeds=False)

    def test_xds_front_proxy_and_service_types(self):
        for front_proxy in (False, True):
            for service_type in ("ClusterIP", "NodePort", "LoadBalancer"):
                v = {
                    "frontProxy": front_proxy,
                    "xds": {"host": "xds.example", "port": 9090},
                    "service": {"type": service_type},
                }
                docs = helm("ingress-dataplane", v)
                service = next(d for d in docs if d["kind"] == "Service")
                self.assertEqual(
                    service["spec"]["ports"][0]["port"], 8080 if front_proxy else 443
                )
                self.assertEqual(
                    "externalTrafficPolicy" in service["spec"],
                    service_type != "ClusterIP",
                )
                config = yaml.safe_load(
                    next(d for d in docs if d["kind"] == "ConfigMap")["data"]["config"]
                )
                socket = config["static_resources"]["clusters"][0]["load_assignment"][
                    "endpoints"
                ][0]["lb_endpoints"][0]["endpoint"]["address"]["socket_address"]
                self.assertEqual(socket, {"address": "xds.example", "port_value": 9090})
        docs = helm("ingress", {"frontProxy": True})
        env = pod_spec(docs)["containers"][0]["env"]
        self.assertIn({"name": "OCTELIUM_FRONT_PROXY_MODE", "value": "true"}, env)

    def test_certificate_names_and_domain(self):
        v = base_values("nocturne")
        v["certificates"] = {
            "enabled": True,
            "issuerRef": {"name": "issuer"},
            "cluster": {"domain": "access.example"},
            "namespaces": [{"name": "team", "dnsNames": ["team.example"]}],
        }
        certs = [d for d in helm("nocturne", v) if d["kind"] == "Certificate"]
        self.assertEqual(
            {c["spec"]["secretName"] for c in certs}, {"cert-cluster", "cert-ns-team"}
        )
        cluster = next(c for c in certs if c["spec"]["secretName"] == "cert-cluster")
        self.assertIn("*.access.example", cluster["spec"]["dnsNames"])
        v["certificates"]["cluster"] = {"dnsNames": ["explicit.example"]}
        certs = [d for d in helm("nocturne", v) if d["kind"] == "Certificate"]
        self.assertEqual(certs[0]["spec"]["dnsNames"], ["explicit.example"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
