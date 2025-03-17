#!/usr/bin/env python3
"""
Hetzner Cloud VPS Management Script

This script allows you to create or delete Hetzner Cloud VPS instances
using the Hetzner Cloud API.
"""

import argparse
import json
import os
import sys
import requests
from typing import Dict, Any, Optional, List

# Default configuration
DEFAULT_NAME = "isaac"
DEFAULT_SERVER_TYPE = "cax41"  # Shared vCPU (ARM64)
DEFAULT_IMAGE = "ubuntu-24.04"
DEFAULT_LOCATION = "nbg1"  # Nuremberg
DEFAULT_SSH_KEY = "hosted-fornet@protonmail.com"


class HetznerCloudManager:
    """Manages Hetzner Cloud VPS instances through their API."""

    API_BASE_URL = "https://api.hetzner.cloud/v1"

    def __init__(self, api_token: str):
        """
        Initialize the Hetzner Cloud Manager.

        Args:
            api_token: The Hetzner Cloud API token
        """
        self.api_token = api_token
        self.headers = {
            "Authorization": f"Bearer {api_token}",
            "Content-Type": "application/json"
        }

    def create_server(self, name: str, server_type: str, image: str, location: str,
                      ssh_keys: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Create a new Hetzner Cloud server.

        Args:
            name: Server name
            server_type: Server type (e.g., cax41)
            image: OS image (e.g., ubuntu-24.04)
            location: Server location (e.g., nbg1)
            ssh_keys: List of SSH key IDs or names to add to the server

        Returns:
            Dict containing the server information
        """
        data = {
            "name": name,
            "server_type": server_type,
            "image": image,
            "location": location,
            "public_net": {
                "enable_ipv4": True,
                "enable_ipv6": True
            }
        }

        if ssh_keys:
            data["ssh_keys"] = ssh_keys

        response = requests.post(
            f"{self.API_BASE_URL}/servers",
            headers=self.headers,
            json=data
        )

        self._check_response(response)
        return response.json()

    def delete_server(self, server_id: str) -> Dict[str, Any]:
        """
        Delete a Hetzner Cloud server.

        Args:
            server_id: The ID of the server to delete

        Returns:
            Dict containing the response information
        """
        response = requests.delete(
            f"{self.API_BASE_URL}/servers/{server_id}",
            headers=self.headers
        )

        self._check_response(response, [204])
        return {"status": "deleted", "server_id": server_id}

    def list_servers(self) -> Dict[str, Any]:
        """
        List all Hetzner Cloud servers.

        Returns:
            Dict containing all server information
        """
        response = requests.get(
            f"{self.API_BASE_URL}/servers",
            headers=self.headers
        )

        self._check_response(response)
        return response.json()

    def get_ssh_keys(self) -> Dict[str, Any]:
        """
        List all SSH keys in the Hetzner Cloud account.

        Returns:
            Dict containing all SSH key information
        """
        response = requests.get(
            f"{self.API_BASE_URL}/ssh_keys",
            headers=self.headers
        )

        self._check_response(response)
        return response.json()

    def _check_response(self, response: requests.Response,
                        success_codes: List[int] = [200, 201]) -> None:
        """
        Check if the API response was successful.

        Args:
            response: The API response
            success_codes: List of status codes considered successful

        Raises:
            SystemExit: If the API request failed
        """
        if response.status_code not in success_codes:
            try:
                error_data = response.json()
                error_message = error_data.get('error', {}).get('message', 'Unknown error')
                print(f"Error: {error_message}")
            except json.JSONDecodeError:
                print(f"Error: HTTP {response.status_code} - {response.text}")
            sys.exit(1)


def create_server(api_manager: HetznerCloudManager, args: argparse.Namespace) -> None:
    """
    Create a new server with the given parameters.

    Args:
        api_manager: The Hetzner Cloud Manager
        args: Command line arguments
    """
    # Get SSH keys if needed
    ssh_key_ids = []
    if args.ssh_keys:  # This will now always be true due to default value
        ssh_keys_response = api_manager.get_ssh_keys()
        all_ssh_keys = ssh_keys_response.get('ssh_keys', [])

        if all_ssh_keys:
            print("Using the following SSH keys:")

        for key_name in args.ssh_keys:
            # Try to find by name or ID
            found = False
            for key in all_ssh_keys:
                if key_name == key['name'] or key_name == str(key['id']):
                    ssh_key_ids.append(key['id'])
                    print(f"  - {key['name']} (ID: {key['id']})")
                    found = True
                    break

            if not found:
                print(f"Warning: SSH key '{key_name}' not found. Skipping.")

    # Create the server
    print(f"\nCreating Hetzner Cloud VPS with the following configuration:")
    print(f"Server Name: {args.name}")
    print(f"Server Type: {args.server_type}")
    print(f"Image: {args.image}")
    print(f"Location: {args.location}")

    response = api_manager.create_server(
        name=args.name,
        server_type=args.server_type,
        image=args.image,
        location=args.location,
        ssh_keys=ssh_key_ids if ssh_key_ids else None
    )

    server = response.get('server', {})
    server_id = server.get('id')
    server_ipv4 = server.get('public_net', {}).get('ipv4', {}).get('ip', 'Not assigned')
    server_ipv6 = server.get('public_net', {}).get('ipv6', {}).get('ip', 'Not assigned')
    root_password = response.get('root_password', 'Not provided (using SSH key)')

    print("\nServer created successfully!")
    print(f"Server ID: {server_id}")
    print(f"IPv4: {server_ipv4}")
    print(f"IPv6: {server_ipv6}")
    print(f"Root Password: {root_password}")
    print("\nYour server is now being provisioned. It may take a few minutes to be fully ready.")
    print(f"You can connect to your server using SSH: ssh root@{server_ipv4}")


def delete_server(api_manager: HetznerCloudManager, args: argparse.Namespace) -> None:
    """
    Delete a server with the given ID or name.

    Args:
        api_manager: The Hetzner Cloud Manager
        args: Command line arguments
    """
    server_id = args.server_id

    # Check if server_id is a name rather than an ID
    if not server_id.isdigit():
        servers_response = api_manager.list_servers()
        servers = servers_response.get('servers', [])

        for server in servers:
            if server['name'] == server_id:
                server_id = str(server['id'])
                print(f"Found server '{args.server_id}' with ID: {server_id}")
                break
        else:
            print(f"Error: Server with name '{args.server_id}' not found.")
            sys.exit(1)

    # Confirm deletion
    if not args.force:
        confirmation = input(f"Are you sure you want to delete server ID {server_id}? [y/N]: ")
        if confirmation.lower() not in ['y', 'yes']:
            print("Deletion cancelled.")
            sys.exit(0)

    print(f"Deleting server ID: {server_id}...")
    result = api_manager.delete_server(server_id)
    print(f"Server {server_id} has been deleted.")


def list_servers(api_manager: HetznerCloudManager, args: argparse.Namespace) -> None:
    """
    List all servers in the Hetzner Cloud account.

    Args:
        api_manager: The Hetzner Cloud Manager
        args: Command line arguments
    """
    response = api_manager.list_servers()
    servers = response.get('servers', [])

    if not servers:
        print("No servers found.")
        return

    print(f"\nFound {len(servers)} servers:\n")
    print(f"{'ID':<10} {'NAME':<20} {'STATUS':<15} {'TYPE':<10} {'IPv4':<15} {'LOCATION':<10}")
    print("-" * 80)

    for server in servers:
        server_id = server.get('id', 'N/A')
        name = server.get('name', 'N/A')
        status = server.get('status', 'N/A')
        server_type = server.get('server_type', {}).get('name', 'N/A')
        ipv4 = server.get('public_net', {}).get('ipv4', {}).get('ip', 'N/A')
        location = server.get('datacenter', {}).get('location', {}).get('name', 'N/A')

        print(f"{server_id:<10} {name:<20} {status:<15} {server_type:<10} {ipv4:<15} {location:<10}")


def main():
    """Main function to parse arguments and execute commands."""
    parser = argparse.ArgumentParser(
        description="Manage Hetzner Cloud VPS instances",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )

    # Add API token argument (can also use environment variable)
    parser.add_argument("-t", "--token",
                        help="Hetzner Cloud API token (can also be set via HETZNER_API_TOKEN env var)")

    # Create subparsers for different commands
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")
    subparsers.required = True

    # Create server command
    create_parser = subparsers.add_parser("create", help="Create a new VPS",
                                         formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    create_parser.add_argument("-n", "--name", default=DEFAULT_NAME,
                              help=f"Server name (default: {DEFAULT_NAME})")
    create_parser.add_argument("-s", "--server-type", default=DEFAULT_SERVER_TYPE,
                              help=f"Server type (default: {DEFAULT_SERVER_TYPE})")
    create_parser.add_argument("-i", "--image", default=DEFAULT_IMAGE,
                              help=f"OS image (default: {DEFAULT_IMAGE})")
    create_parser.add_argument("-l", "--location", default=DEFAULT_LOCATION,
                              help=f"Server location (default: {DEFAULT_LOCATION})")
    create_parser.add_argument("-k", "--ssh-keys", nargs="+", default=[DEFAULT_SSH_KEY],
                              help=f"SSH key IDs or names to add to the server (default: {DEFAULT_SSH_KEY})")
    create_parser.set_defaults(func=create_server)

    # Delete server command
    delete_parser = subparsers.add_parser("delete", help="Delete a VPS",
                                         formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    delete_parser.add_argument("server_id", nargs="?", default=DEFAULT_NAME,
                              help=f"Server ID or name to delete (default: {DEFAULT_NAME})")
    delete_parser.add_argument("-f", "--force", action="store_true",
                              help="Force deletion without confirmation (default: False)")
    delete_parser.set_defaults(func=delete_server)

    # List servers command
    list_parser = subparsers.add_parser("list", help="List all VPS instances",
                                       formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    list_parser.set_defaults(func=list_servers)

    args = parser.parse_args()

    # Get API token from arguments or environment
    api_token = args.token or os.environ.get("HETZNER_API_TOKEN")
    if not api_token:
        parser.error("API token is required. Provide it with --token or set HETZNER_API_TOKEN environment variable.")

    # Initialize Hetzner Cloud Manager and execute the selected command
    api_manager = HetznerCloudManager(api_token)
    args.func(api_manager, args)


if __name__ == "__main__":
    main()
