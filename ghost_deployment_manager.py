import os
import boto3
import paramiko
import json
import pandas as pd
from sqlalchemy import create_engine, text
from dataclasses import dataclass
from typing import Optional, List, Dict, Tuple
from helping_page import *
from dotenv import load_dotenv
load_dotenv()

# Global Configuration
BASE_URL = AUTO_BLOG_BASE_URL
SNAPSHOT_IMAGE = "ghost-0-backup"
PRIMARY_INSTANCE = "54.190.4.4"
DOCKER_FLEET_REGION = "us-west-2"
INSTANCE_PLAN = "small_3_0"
SSH_PEM = 'Logos/rsa/docker_ghost.pem'
USER_DATA_BASE_DIR = '/home/ubuntu/ghost_user_data'
NGINX_SITES_AVAILABLE = '/etc/nginx/sites-available'
NGINX_SITES_ENABLED = '/etc/nginx/sites-enabled'
SSL_CERT_PATH = '/etc/letsencrypt/live/enspiring.org/fullchain.pem'
SSL_KEY_PATH = '/etc/letsencrypt/live/enspiring.org/privkey.pem'
EMAIL_ADDRESS = os.getenv("GMAIL_ADDRESS_ADMIN")
EMAIL_PASSWORD = os.getenv("GMAIL_PASSWORD_ADMIN")
MAX_INSTANCES_PER_SERVER = 5

SSH_USER = "ubuntu"

@dataclass
class LightsailInstance:
    instance_name: str
    public_ip: str
    private_ip: str
    region: str
    ghost_instances: int = 0
    max_instances: int = MAX_INSTANCES_PER_SERVER

class GhostDeploymentManager:
    def __init__(self, 
                 primary_instance: str = PRIMARY_INSTANCE,
                 region: str = DOCKER_FLEET_REGION,
                 snapshot_name: str = SNAPSHOT_IMAGE,
                 instance_plan: str = INSTANCE_PLAN):
        self.primary_instance = primary_instance
        self.region = region
        self.snapshot_name = snapshot_name
        self.instance_plan = instance_plan
        self.lightsail_client = boto3.client('lightsail', region_name=region)
        self.base_dir = os.getcwd()
        self.instances: Dict[str, LightsailInstance] = self._load_instances()

    def _load_instances(self) -> Dict[str, LightsailInstance]:
        """Load existing Lightsail instances and their Ghost instance counts"""
        instances = {}
        try:
            response = self.lightsail_client.get_instances()
            for instance in response['instances']:
                if instance['name'].startswith('ghost-'):
                    instances[instance['name']] = LightsailInstance(
                        instance_name=instance['name'],
                        public_ip=instance['publicIpAddress'],
                        private_ip=instance['privateIpAddress'],
                        region=self.region
                    )
                    # Get ghost instance count through SSH
                    self._update_instance_count(instances[instance['name']])

        except Exception as e: send_debug_to_laogege(f"Error loading instances: {e}")
        return instances

    def _update_instance_count(self, instance: LightsailInstance):
        """Get number of running Ghost instances via SSH"""
        ssh = self._get_ssh_client(instance.public_ip)
        try:
            stdin, stdout, stderr = ssh.exec_command("docker ps | grep ghost | wc -l")
            instance.ghost_instances = int(stdout.read().decode().strip())

        except Exception as e: send_debug_to_laogege(f"Error updating instance count: {e}")

        finally: ssh.close()

    def _get_ssh_client(self, host: str) -> paramiko.SSHClient:
        """Create SSH client for instance management"""
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        key_path = os.path.join(self.base_dir, SSH_PEM)
        try:
            ssh.connect(
                hostname=host,
                username='ubuntu',
                key_filename=key_path,
                timeout=10
            )
            return ssh
        
        except Exception as e:
            send_debug_to_laogege(f"SSH connection failed: {e}")
            raise

    def wait_for_ssh(self, public_ip: str, max_attempts: int = 24) -> bool:
        """Wait for SSH to become available on the instance"""
        print(f"Waiting for SSH to become available on public IP {public_ip}...")

        for attempt in range(max_attempts):

            try:
                ssh = self._get_ssh_client(public_ip)
                ssh.close()
                return True
            
            except Exception as e:
                if attempt >= 5: send_debug_to_laogege(f"Attempt {attempt + 1}/{max_attempts}: SSH not ready yet on {public_ip}: {e}")
                time.sleep(20)

        return False

    def _create_new_instance(self) -> LightsailInstance:
        """Create new Lightsail instance from snapshot"""
        instance_count = len(self.instances)
        instance_name = f"ghost-{instance_count + 1}"
        try:
            send_debug_to_laogege(f"Creating new instance: {instance_name}")
            self.lightsail_client.create_instances_from_snapshot(
                instanceNames=[instance_name],
                availabilityZone=f'{self.region}a',
                bundleId=self.instance_plan,
                instanceSnapshotName=self.snapshot_name
            )
            send_debug_to_laogege(f"Waiting for instance {instance_name} to be ready...")

            for _ in range(60):
                try:
                    response = self.lightsail_client.get_instance(
                        instanceName=instance_name
                    )
                    state = response['instance']['state']['name']
                    print(f"Instance state: {state}")

                    if state == 'running': break

                    time.sleep(10)

                except: time.sleep(10)

            else: raise TimeoutError("Instance failed to reach running state in time")
            
            response = self.lightsail_client.get_instance(instanceName=instance_name)
            public_ip = response['instance']['publicIpAddress']
            private_ip = response['instance']['privateIpAddress']

            send_debug_to_laogege(f"Instance \npublic IP: {public_ip}\nprivate IP: {private_ip}")

            instance = LightsailInstance(
                instance_name=instance_name,
                public_ip=public_ip,
                private_ip=private_ip,
                region=self.region
            )
            if not self.wait_for_ssh(public_ip): raise TimeoutError("SSH service failed to become available")

            self.initialize_instance(instance)
            return instance
        
        except Exception as e:
            send_debug_to_laogege(f"Error creating new instance: {e}")
            raise

    def initialize_instance(self, instance: LightsailInstance):
        """Initialize new instance by cleaning up existing Ghost installations"""
        send_debug_to_laogege(f"Starting instance initialization: {instance.instance_name}")
        ssh = self._get_ssh_client(instance.public_ip)
        try:
            commands = [
                "sudo docker stop $(docker ps -a -q) || true",
                "sudo docker rm $(docker ps -a -q) || true",
                f"sudo find {NGINX_SITES_ENABLED}/ -type l -exec unlink {{}} \;",
                f"sudo rm -f {NGINX_SITES_AVAILABLE}/*",
                f"sudo rm -rf {USER_DATA_BASE_DIR}/* && sudo chown -R ubuntu:ubuntu {USER_DATA_BASE_DIR}",
                f"sudo mkdir -p {USER_DATA_BASE_DIR} && sudo chown -R ubuntu:ubuntu {USER_DATA_BASE_DIR}"
            ]
            for cmd in commands:
                print(f"Executing: {cmd}")
                stdin, stdout, stderr = ssh.exec_command(cmd)
                exit_status = stdout.channel.recv_exit_status()
                if exit_status != 0:
                    error = stderr.read().decode().strip()
                    print(f"Command failed with status {exit_status}: {error}")
            send_debug_to_laogege(f"Instance initialization completed: {instance.instance_name}")

        except Exception as e: raise e

        finally: ssh.close()

    def _update_nginx_config(self, username: str, instance: LightsailInstance, port: int):
        """Update Nginx configuration on primary instance"""
        ssh = self._get_ssh_client(self.primary_instance)
        try:
            config = f"""
server {{
    listen 80;
    server_name {username}.{BASE_URL};
    return 301 https://{username}.{BASE_URL}$request_uri;
}}

server {{
    listen 443 ssl;
    server_name {username}.{BASE_URL};
    ssl_certificate {SSL_CERT_PATH};
    ssl_certificate_key {SSL_KEY_PATH};
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    client_max_body_size 100M;

    location / {{
        proxy_pass http://{instance.private_ip}:{port};
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }}
}}
"""
            config_path = f"/tmp/nginx_config_{username}.conf"
            final_config_path = f"{NGINX_SITES_AVAILABLE}/{username}.{BASE_URL}.conf"

            # Write config to a temporary file on the local machine
            with open(config_path, 'w') as f: f.write(config)

            # Use SCP to upload the configuration to the server
            from scp import SCPClient
            with SCPClient(ssh.get_transport()) as scp: scp.put(config_path, config_path)

            # Move the configuration to the final destination with correct permissions
            cmd = f'sudo mv {config_path} {final_config_path} && sudo chown root:root {final_config_path} && sudo chmod 644 {final_config_path}'
            stdin, stdout, stderr = ssh.exec_command(cmd)
            exit_status = stdout.channel.recv_exit_status()
            if exit_status != 0:
                error = stderr.read().decode().strip()
                raise Exception(f"Failed to move nginx config: {error}")

            # Create a symbolic link to enable the site and reload nginx
            commands = [
                f"if [ -L {NGINX_SITES_ENABLED}/{username}.{BASE_URL}.conf ]; then sudo unlink {NGINX_SITES_ENABLED}/{username}.{BASE_URL}.conf; fi",
                f"sudo ln -s {final_config_path} {NGINX_SITES_ENABLED}/",
                "sudo nginx -t",
                "sudo systemctl reload nginx"
            ]

            for cmd in commands:
                stdin, stdout, stderr = ssh.exec_command(cmd)
                exit_status = stdout.channel.recv_exit_status()
                if exit_status != 0:
                    error = stderr.read().decode().strip()
                    print(f"Command failed with status {exit_status}: {error}")
                    if cmd == "sudo nginx -t": raise Exception(f"Nginx configuration test failed: {error}")

        finally: ssh.close()

    def _get_next_available_port(self, ssh: paramiko.SSHClient) -> int:
        """Get the next available port for Docker container"""
        stdin, stdout, stderr = ssh.exec_command("docker ps --format '{{.Ports}}' | grep -oP '(?<=0.0.0.0:)\d+(?=->2368)' | sort -n | tail -1")
        last_port = stdout.read().decode().strip()
        port = 2368 if not last_port else int(last_port) + 1
        return port

    def deploy_ghost_instance(self, username: str, existing_private_ip: Optional[str] = None) -> Tuple[str, LightsailInstance]:
        """
        Deploy a new Ghost instance for the given username
        Returns the blog URL and the instance used
        """
        target_instance = None
        if existing_private_ip:
            # Find the instance with this private IP in self.instances
            for instance in self.instances.values():
                if instance.private_ip == existing_private_ip:
                    target_instance = instance
                    break
            if not target_instance:
                raise ValueError(f"No instance found with private IP {existing_private_ip}")
            if target_instance.ghost_instances >= target_instance.max_instances:
                send_debug_to_laogege(f"Instance {target_instance.instance_name} has reached max capacity. Creating a new instance.")
                target_instance = self._create_new_instance()
                self.instances[target_instance.instance_name] = target_instance
        else:
            # Original logic: find an instance that has capacity
            for instance in self.instances.values():
                if instance.ghost_instances < instance.max_instances:
                    target_instance = instance
                    break
            if not target_instance:
                target_instance = self._create_new_instance()
                self.instances[target_instance.instance_name] = target_instance

        ssh = self._get_ssh_client(target_instance.public_ip)
        try:
            # Find the next available port
            port = self._get_next_available_port(ssh)
            user_dir = f"{USER_DATA_BASE_DIR}/{username}"
            commands = [
                f"mkdir -p {user_dir}/config",
                self._get_ghost_config_command(username, user_dir),
                self._get_docker_run_command(username, port, user_dir)
            ]
            for cmd in commands:
                stdin, stdout, stderr = ssh.exec_command(cmd)
                exit_status = stdout.channel.recv_exit_status()
                if exit_status != 0:
                    error = stderr.read().decode().strip()
                    print(f"Command '{cmd}' failed: {error}")
                    raise Exception(f"Deployment command failed: {error}")
            target_instance.ghost_instances += 1
            self._update_nginx_config(username, target_instance, port)

            return f"https://{username}.{BASE_URL}", target_instance
        
        finally: ssh.close()

    def _get_ghost_config_command(self, username: str, user_dir: str) -> str:
        """Generate Ghost config creation command"""
        config = {
            "url": f"https://{username}.{BASE_URL}",
            "database": {
                "client": "sqlite3",
                "connection": {
                    "filename": "/var/lib/ghost/content/data/ghost.db"
                }
            },
            "server": {
                "port": 2368,
                "host": "0.0.0.0"
            },
            "mail": {
                "transport": "SMTP",
                "options": {
                    "service": "Gmail",
                    "auth": {
                        "user": EMAIL_ADDRESS,
                        "pass": EMAIL_PASSWORD
                    }
                }
            }
        }
        config_json = json.dumps(config, indent=2)
        return f'echo \'{config_json}\' > {user_dir}/config/config.production.json'

    def _get_docker_run_command(self, username: str, port: int, user_dir: str) -> str:
        """Generate Docker run command"""
        return f"""
docker run -d \
  --name "{username}" \
  -e url=https://{username}.{BASE_URL} \
  -p {port}:2368 \
  -v "{user_dir}:/var/lib/ghost/content" \
  -v "{user_dir}/config/config.production.json:/var/lib/ghost/config.production.json" \
  --restart always \
  ghost:latest
"""
    

def get_next_server_ip(missing_id: int, existing_ids_df: pd.DataFrame) -> str:
    """
    Determine which server's IP to use for a missing ID slot.
    
    Args:
        missing_id: The ID slot we're filling
        existing_ids_df: DataFrame with existing IDs and their server IPs
    
    Returns:
        The internal IP address to use
    """
    if (missing_id - 1) % MAX_INSTANCES_PER_SERVER == 0:
        # Previous server was full, look at next higher ID's server
        higher_ids = existing_ids_df[existing_ids_df['Auto_blog_id'] > missing_id]
        if not higher_ids.empty:
            return higher_ids.iloc[0]['Docker_internal_ip']
    else:
        # Previous server had space, look at previous ID's server
        lower_ids = existing_ids_df[existing_ids_df['Auto_blog_id'] < missing_id]
        if not lower_ids.empty:
            return lower_ids.iloc[-1]['Docker_internal_ip']
    return None


def create_ghost_blog(sub_domain_name: str, chat_id: str, token=TELEGRAM_BOT_TOKEN, engine=engine):
    # Step 1: Check if subdomain name is unique
    df = pd.read_sql(
        text("SELECT Sub_domain_name FROM chat_id_parameters WHERE Sub_domain_name = :sub_domain_name"),
        engine,
        params={'sub_domain_name': sub_domain_name}
    )
    if not df.empty:
        return send_message(
            OWNER_CHAT_ID,
            f"Sorry, `{sub_domain_name}` has been used, try another name.\n\nhttps://{sub_domain_name}.{AUTO_BLOG_BASE_URL}",
            token
        )

    # Step 2: Fetch all existing Auto_blog_ids and Docker information
    df = pd.read_sql(
        text("""
            SELECT Auto_blog_id, Docker_internal_ip, Docker_public_ip 
            FROM chat_id_parameters 
            WHERE Auto_blog_id IS NOT NULL 
            ORDER BY Auto_blog_id
        """),
        engine
    )

    if df.empty:
        max_blog_id = 0
        Docker_internal_ip = None
    else:
        max_blog_id = df['Auto_blog_id'].max()
        # Get list of existing IDs
        existing_ids = set(df['Auto_blog_id'].values)
        # Find gaps in ID sequence from 1 to max_id
        all_possible_ids = set(range(1, max_blog_id + 1))
        missing_ids = sorted(all_possible_ids - existing_ids)

        if missing_ids:
            # Use the first available gap
            new_auto_blog_id = missing_ids[0]
            # Determine which server's IP to use
            Docker_internal_ip = get_next_server_ip(new_auto_blog_id, df)
        else:
            # No gaps, proceed with normal logic
            new_auto_blog_id = max_blog_id + 1
            if max_blog_id % MAX_INSTANCES_PER_SERVER == 0:
                Docker_internal_ip = None  # Will create new server
            else:
                Docker_internal_ip = df.iloc[-1]['Docker_internal_ip']

    print(f"New Auto_blog_id: {new_auto_blog_id}, Docker_internal_ip: {Docker_internal_ip}")

    # Now deploy the Ghost instance
    manager = GhostDeploymentManager()

    try:
        blog_url, instance = manager.deploy_ghost_instance(sub_domain_name, Docker_internal_ip)
    except Exception as e:
        return send_debug_to_laogege(f"Create ghost blog for `{sub_domain_name}` failed: \n\n{e}")

    # Save user's data
    with engine.begin() as conn:
        conn.execute(
            text("""
                UPDATE chat_id_parameters 
                SET Auto_blog_id = :auto_blog_id, 
                    Sub_domain_name = :sub_domain_name, 
                    ghost_api_url = :ghost_api_url, 
                    Docker_internal_ip = :docker_internal_ip, 
                    Docker_public_ip = :docker_public_ip 
                WHERE chat_id = :chat_id
            """),
            {
                'auto_blog_id': new_auto_blog_id,
                'sub_domain_name': sub_domain_name,
                'docker_internal_ip': instance.private_ip,
                'docker_public_ip': instance.public_ip,
                'ghost_api_url': blog_url,
                'chat_id': chat_id
            }
        )

    send_message(
        OWNER_CHAT_ID,
        f"New Ghost blog created: \n{blog_url}\n\nDashboard url:\n{blog_url}/ghost",
        token
    )
    return send_message(
        chat_id,
        f"Your Ghost Auto Blog has been created: \n\n{blog_url}\n\nDashboard url:\n{blog_url}/ghost",
        token
    )


def remove_ghost_user(chat_id):
    """
    SSH into the Ghost server and remove a user's blog instance.
    First makes the remove_user.sh script executable, then runs it.
    
    Args:
        username: The username of the Ghost blog to remove
        private_ip: The private IP address of the Ghost server
    
    Returns:
        bool: True if successful, False otherwise
    """

    df = pd.read_sql(text("SELECT Docker_internal_ip, Sub_domain_name FROM chat_id_parameters WHERE chat_id = :chat_id"), engine,params={'chat_id': chat_id})
    if not df.empty: return send_message(OWNER_CHAT_ID, f"Can't find the user's blog subdomain with chat_id: {chat_id}")

    private_ip = df['Docker_internal_ip'].values[0]
    username = df['Sub_domain_name'].values[0]

    try:
        # Verify PEM file exists
        if not os.path.exists(SSH_PEM):
            print(f"Error: PEM file not found at {SSH_PEM}")
            return False

        # Input validation for IP address format
        if not private_ip:
            print("Error: Private IP address is required")
            return False

        # First, make the script executable
        chmod_cmd = [
            "ssh",
            "-i", SSH_PEM,
            "-o", "StrictHostKeyChecking=no",
            f"{SSH_USER}@{private_ip}",
            "chmod +x /home/ubuntu/ghost_user_data/remove_user.sh"
        ]

        print("Making remove_user.sh executable...")
        chmod_process = subprocess.run(
            chmod_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        if chmod_process.returncode != 0:
            print("Failed to make script executable")
            print("Error output:")
            print(chmod_process.stderr)
            return False

        # Now execute the removal script
        remove_cmd = [
            "ssh",
            "-i", SSH_PEM,
            "-o", "StrictHostKeyChecking=no",
            f"{SSH_USER}@{private_ip}",
            f"cd /home/ubuntu/ghost_user_data && ./remove_user.sh {username}"
        ]

        print(f"Removing Ghost blog for user: {username} on server: {private_ip}")
        process = subprocess.run(
            remove_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        # Check if the command was successful
        if process.returncode == 0:
            print("Successfully removed Ghost blog instance")
            print(process.stdout)

            # Update the database
            with engine.begin() as conn:
                conn.execute(
                    text("""
                        UPDATE chat_id_parameters 
                        SET 
                            Auto_blog_id = NULL, 
                            Sub_domain_name = NULL, 
                            ghost_api_url = NULL, 
                            Docker_internal_ip = NULL, 
                            Docker_public_ip = NULL
                        WHERE 
                            chat_id = :chat_id"""),
                    {'chat_id': chat_id}
                )
            send_debug_to_laogege(f"/chat_{chat_id} | {username} | Ghost blog instance removed successfully, {private_ip} database updated.")
            return True
        else:
            print("Failed to remove Ghost blog instance")
            print("Error output:")
            print(process.stderr)
            return False 

    except Exception as e:
        print(f"An error occurred: {str(e)}")
        return False



if __name__ == "__main__":
    print("Creating Ghost blog...")
    create_ghost_blog('elvis', '5504365532')