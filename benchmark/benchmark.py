# Python 2/3 compatibility
from __future__ import print_function

try:
    from urllib.parse import quote
    from urllib.request import urlopen
except ImportError:
    from urllib import quote
    from urllib2 import urlopen

from catalog import append_to_catalog
from characterization import characterize_data
from zipfile import ZipFile
from time import sleep
import argparse
import io
import shutil
import os
import subprocess
import json


def configure_prometheus(namespace):
    """Configures a cluster to use Prometheus.

    Fetches the prometheus-recipes repo and runs the script from there to configure the cluster to use it.

    Args:
        namespace: Comma-separated list of namespaces for Prometheus to watch
    """

    shutil.rmtree("./temp", ignore_errors=True)
    result = urlopen(
        "https://github.com/carbonrelay/prometheus-recipes/archive/0.0.1.zip"
    )

    zip = ZipFile(io.BytesIO(result.read()))
    zip.extractall(".")

    os.rename("prometheus-recipes-0.0.1", "temp")

    # ZipFile's extractall method messes up files permissions, so we need to add execute permissions back.
    os.chmod("./temp/prometheus-recipes.sh", 0o755)
    os.chmod("./temp/prometheus.sh", 0o755)

    # Script occasionally fails to deploy one or two things on the first pass.  Do it twice.
    subprocess.call(["./temp/prometheus-recipes.sh", namespace, "-npk"])
    subprocess.call(["./temp/prometheus-recipes.sh", namespace, "-npk"])


def heartbeat(period, update_file, duration=300):
    if period <= 0:
        sleep(duration)
    else:
        time = 0
        while time < duration:
            top = top_nodes()

            output = {"cpu": top[0], "memory": top[1], "messages": top[2]}

            print(json.dumps(output), file=update_file)
            update_file.flush()
            time += period
            sleep(period)


def top_nodes():
    """Retrieves current memory/cpu usage of nodes.

    Fetches current usage of ndoes in the cluster.  Retrieves values as percentages and then averages those percents
    against the current number of nodes in the cluster.

    Returns:
        A tuple (cpu usage, memory usage) representing current usage by the nodes.
    """

    node_lines = ""
    while node_lines == "":
        try:
            node_lines = subprocess.check_output(
                ["kubectl", "top", "nodes", "--no-headers"]
            ).split()
        except subprocess.CalledProcessError as e:
            print(e.output)
            print("Reattempting retrieving node cpu and memory")

    messages = prometheus_query("avg(rate(bps_messages_total[1m]))")
    length = len(node_lines)

    cpu = memory = 0
    for index in range(0, length, 5):
        cpu += float(node_lines[index + 2][:-1])
        memory += float(node_lines[index + 4][:-1])

    length /= 5
    return (cpu / length, memory / length, messages)


def prometheus_query(query):
    """Performs a query against prometheus.

    Utilizes kubectl to execute a command within the prometheus container.  Assumes that the query given
    only returns one value and only returns that value.  If the query given does not return a value, this
    will return -1 instead of erroring out.

    Args:
        query - Prometheus QL query to make.  Should only fetch one value.

    Returns:
        A single float representing the result of the provided query.
    """
    query_url = "http://localhost:9090/prometheus/api/v1/query?query=" + quote(
        query, safe="~@#$&()*!+=:;,.?/'"
    )
    response = subprocess.check_output(
        [
            "kubectl",
            "exec",
            "prometheus-k8s-0",
            "-n",
            "monitoring",
            "-c",
            "prometheus",
            "--",
            "wget",
            "-O",
            "-",
            "-q",
            query_url,
        ]
    )

    parsed_response = json.loads(response)

    # Make sure that if prometheus doesn't have the data that we just return peacefully
    result = parsed_response["data"]["result"]
    if len(result) > 0:
        value = result[0]["value"]
        if len(value) > 1:
            return float(value[1])

    return -1


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "generators",
        type=int,
        default=-1,
        nargs="?",
        help="The maximum number of generators to run as part of this test.  "
        + "If the number is less than 1, it will run until it observes a decrease in the message throughput in Kafka",
    )
    parser.add_argument(
        "-r",
        "--redis",
        action="store_true",
        help="Include Redis in Kapture as part of the test",
    )
    parser.add_argument(
        "-e",
        "--elasticsearch",
        action="store_true",
        help="Include Elasticsearch (and Logstash) in Kapture as part of the test",
    )
    parser.add_argument(
        "--characterize",
        action="store_true",
        help="Configures a heartbeat for Kapture to use while waiting for the benchmark.  The heartbeat specifies the "
        + "time (in seconds) for Kapture to wait before pinging the server to get cpu/memory statistics.  These stats "
        + "are then stored in the updates.json file next to results.json.  If the value for the heartbeat is less "
        + "than or equal to 0, the heartbeat will not trigger; this is the default behavior",
    )
    parser.add_argument(
        "--update-catalog",
        action="store_true",
        help="Update the catalog.json with data from this run and also persist the data into the results folder",
    )
    parser.add_argument(
        "--heartbeat",
        type=int,
        default=-1,
        help="Attempts to characterize the performance of the cluster based on previously collected data.  "
        + "Will run at the end after the benchmark.",
    )
    args = parser.parse_args()

    heartbeat_period = int(args.heartbeat)
    max_generators = int(args.generators)
    characterize = args.characterize
    update_catalog = args.update_catalog
    namespace = "test"

    configure_prometheus(namespace)

    os.chdir("..")

    with open("./benchmark/temp/results.json", "w") as results, open(
        "./benchmark/temp/updates.json", "w"
    ) as updates:
        result_data = {
            "configuration": {"elasticsearch": args.elasticsearch, "redis": args.redis},
            "data": [],
        }

        flags = "-p"
        if args.redis:
            flags = flags + "r"
        if args.elasticsearch:
            flags = flags + "e"

        subprocess.check_output(["./kapture.sh", namespace, "1", flags])

        last_message_rate = 0
        messages_declining = False
        generators = 1
        while (
            max_generators <= 0 and not messages_declining
        ) or generators <= max_generators:
            heartbeat(heartbeat_period, updates)

            cpu, memory, _ = top_nodes()
            network = prometheus_query(
                "sum(rate(node_network_receive_bytes_total[3m]))"
            )
            disk = prometheus_query("sum(rate(node_disk_written_bytes_total[3m]))")

            messages = prometheus_query("avg(rate(bps_messages_total[3m]))")

            data = {
                "generators": generators,
                "cpu": cpu,
                "memory": memory,
                "network": network,
                "disk": disk,
                "messages": messages,
            }

            print(json.dumps(data), file=updates)
            updates.flush()
            result_data["data"].append(data)

            if messages_declining or last_message_rate > messages:
                messages_declining = True
            else:
                last_message_rate = messages

            generators += 1
            subprocess.check_output(
                [
                    "kubectl",
                    "scale",
                    "Deployment",
                    "data-loader",
                    "-n",
                    namespace,
                    "--replicas",
                    str(generators),
                ]
            )

        json.dump(result_data, results, indent=4)

    if update_catalog:
        print("Updating catalog with new values")
        append_to_catalog("./benchmark/temp/results.json", "./benchmark/results")

    if characterize:
        print("\nCharacterizing data from benchmark\n")
        characterize_data(result_data)
        print("\n")

    print("Removing created Kapture resources from the cluster...")
    subprocess.check_output(["./kapture.sh", namespace, "--delete"])
    os.chdir("benchmark/temp")
    print("Removing created Prometheus resources from the cluster...")
    subprocess.check_output(["./prometheus-recipes.sh", namespace, "--delete"])
    print("Cleaning up created testing namespace...")
    subprocess.check_output(["kubectl", "delete", "namespace", namespace])


if __name__ == "__main__":
    main()
