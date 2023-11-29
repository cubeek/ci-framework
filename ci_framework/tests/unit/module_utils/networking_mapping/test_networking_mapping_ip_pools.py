from __future__ import absolute_import, division, print_function


__metaclass__ = type

import ipaddress

import pytest
from ansible_collections.cifmw.general.plugins.module_utils.networking_mapping import (
    exceptions,
    ip_pools,
    networking_definition,
)
from ansible_collections.cifmw.general.tests.unit.module_utils.test_utils import (
    networking_mapping_stub_data,
)


def test_ip_pool_ipv4_ok():
    pool_range = networking_definition.HostNetworkRange(
        ipaddress.ip_network("192.168.122.0/24"), start=100, length=3
    )

    pool = ip_pools.IPPool(pool_range)
    base_ip = ipaddress.IPv4Address("192.168.122.100")
    assert pool.get_ip() == base_ip
    assert pool.get_ip() == base_ip + 1
    assert pool.get_ip() == base_ip + 2
    assert pool_range == pool.range


def test_ip_pool_ipv4_reserve_ok():
    pool = ip_pools.IPPool(
        networking_definition.HostNetworkRange(
            ipaddress.ip_network("192.168.122.0/24"), start=100, length=3
        ),
        reservations=["192.168.122.101"],
    )
    base_ip = ipaddress.IPv4Address("192.168.122.100")
    assert pool.get_ip() == base_ip
    assert pool.get_ip() == base_ip + 2

    pool2 = ip_pools.IPPool(
        networking_definition.HostNetworkRange(
            ipaddress.ip_network("192.168.122.0/24"), start=100, length=3
        ),
        reservations=[ipaddress.IPv4Address("192.168.122.100")],
    )
    assert pool2.get_ip() == base_ip + 1
    assert pool2.get_ip() == base_ip + 2


def test_ip_pool_ipv4_reserve_method_ok():
    pool = ip_pools.IPPool(
        networking_definition.HostNetworkRange(
            ipaddress.ip_network("192.168.122.0/24"), start=100, length=5
        ),
    )
    base_ip = ipaddress.IPv4Address("192.168.122.100")
    pool.add_reservation(base_ip + 1)
    pool.add_reservation(str(base_ip + 3))
    assert pool.get_ip() == base_ip
    assert pool.get_ip() == base_ip + 2
    assert pool.get_ip() == base_ip + 4


def test_ip_pool_ipv4_exhausted_fail():
    pool = ip_pools.IPPool(
        networking_definition.HostNetworkRange(
            ipaddress.ip_network("192.168.122.0/24"), start=100, length=1
        ),
    )
    assert pool.get_ip() == ipaddress.IPv4Address("192.168.122.100")
    with pytest.raises(exceptions.NetworkMappingError):
        pool.get_ip()


def test_ip_pool_ipv4_reserve_out_of_range():
    with pytest.raises(exceptions.NetworkMappingError) as exc_info:
        ip_pools.IPPool(
            networking_definition.HostNetworkRange(
                ipaddress.ip_network("192.168.122.0/24"), start=100, length=3
            ),
            reservations=["192.168.122.10"],
        )
    assert "out of range " in str(exc_info.value)


def test_host_ip_pool_manager_get_ip_ok():
    (
        networks_definitions,
        hosts_templates,
    ) = networking_mapping_stub_data.build_valid_network_definition_and_templates_set()
    first_net = list(networks_definitions.values())[0]
    second_net = list(networks_definitions.values())[1]
    first_group = list(hosts_templates.values())[0]
    second_group = list(hosts_templates.values())[1]
    ip_pool_manager = ip_pools.IPPoolsManager(hosts_templates)
    ip_pool_manager.add_instance_reservation(
        first_net.name, ipaddress.ip_address("192.168.122.2")
    )
    ip_pool_manager.add_instance_reservation(
        second_net.name, ipaddress.ip_address("192.168.0.60")
    )
    instance_name_1 = "instance-1"
    instance_name_2 = "instance-2"
    assert ip_pool_manager.get_ip(
        first_group.group_name, first_net.name, instance_name_1
    ) == ipaddress.IPv4Address("192.168.122.1")
    assert ip_pool_manager.get_ip(
        first_group.group_name, first_net.name, instance_name_2
    ) == ipaddress.IPv4Address("192.168.122.3")
    assert ip_pool_manager.get_ip(
        first_group.group_name, first_net.name, instance_name_1
    ) == ipaddress.IPv4Address("192.168.122.1")

    assert ip_pool_manager.get_ip(
        second_group.group_name, second_net.name, instance_name_1
    ) == ipaddress.IPv4Address("192.168.0.61")


def test_host_ip_pool_manager_get_ip_unknown_fail():
    (
        networks_definitions,
        hosts_templates,
    ) = networking_mapping_stub_data.build_valid_network_definition_and_templates_set()
    first_net = list(networks_definitions.values())[0]
    first_group = list(hosts_templates.values())[0]

    ip_pool_manager = ip_pools.IPPoolsManager(hosts_templates)
    with pytest.raises(exceptions.NetworkMappingError) as exc_info:
        ip_pool_manager.get_ip("not-existing-group", first_net.name, "test-instance")
    assert "not-existing-group" in str(exc_info.value)

    with pytest.raises(exceptions.NetworkMappingError) as exc_info:
        ip_pool_manager.get_ip(
            first_group.group_name, "not-existing-net", "test-instance"
        )
    assert "not-existing-net" in str(exc_info.value)