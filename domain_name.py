from helping_page import *
from typing import Optional, Dict, Any, List

PRIMARY_INSTANCE_IP_ADDRESS = "54.190.4.4"

class NameComAPI:
    def __init__(self, username: str, token: str, api_url: str = "https://api.name.com/v4"):
        """
        初始化 Name.com API 客户端
        """
        self.username = username
        self.token = token
        self.api_url = api_url
        self.session = requests.Session()
        self.session.auth = (username, token)
        self.session.headers.update({
            "Content-Type": "application/json"
        })
        
        # 验证凭据
        try:
            test_response = self.session.get(f"{self.api_url}/hello")
            test_response.raise_for_status()
            print("API 连接测试成功")
        except requests.exceptions.RequestException as e:
            print(f"API 连接测试失败: {str(e)}")
            print(f"使用的凭据 - Username: {username}, Token: {'*' * len(token)}")
            if hasattr(e.response, 'text'):
                print(f"错误详情: {e.response.text}")
            raise Exception("API 认证失败")


    def check_domain_status(self, domain_name: str) -> Dict[str, Any]:
        """检查域名状态"""
        endpoint = f"{self.api_url}/domains:checkAvailability"
        data = {"domainNames": [domain_name]}
        
        try:
            print(f"\n正在检查域名: {domain_name}")
            response = self.session.post(endpoint, json=data)
            response_json = response.json()
            
            # 检查域名是否已注册
            try:
                # 尝试获取域名信息
                domain_info = self.session.get(f"{self.api_url}/domains/{domain_name}")
                if domain_info.status_code == 200:
                    return {
                        'available': False,
                        'status': 'registered',
                        'message': f'域名 {domain_name} 已被注册'
                    }
            except:
                pass

            # 检查域名是否可以注册
            search_response = self.session.get(
                f"{self.api_url}/domains/search",
                params={"keyword": domain_name}
            )
            search_data = search_response.json()
            
            if response_json or search_data.get('results'):
                if response_json.get('results'):
                    result = response_json['results'][0]
                    if result.get('purchasable'):
                        return {
                            'available': True,
                            'status': 'available',
                            'price': result.get('purchasePrice'),
                            'message': f'域名可注册，价格: ${result.get("purchasePrice", "未知")}/年'
                        }
                
                return {
                    'available': False,
                    'status': 'registered',
                    'message': f'域名 {domain_name} 已被注册'
                }
            else:
                return {
                    'available': False,
                    'status': 'unknown',
                    'message': f'域名 {domain_name} 不可用或不支持注册'
                }
                
        except requests.exceptions.RequestException as e:
            error_msg = f"检查域名状态失败: {str(e)}"
            print(f"错误: {error_msg}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"错误响应: {e.response.text}")
            return {
                'available': False,
                'status': 'error',
                'message': error_msg
            }


    def search_domains(self, keyword: str, tlds: List[str] = None) -> Dict[str, Any]:
        """
        搜索可用域名并返回建议
        """
        if tlds is None:
            tlds = [".com", ".ai", ".net", ".org", ".io", ".co", ".app", ".dev", ".tech", ".me"]
        
        domain_names = [f"{keyword}{tld}" for tld in tlds]
        endpoint = f"{self.api_url}/domains:checkAvailability"
        data = {"domainNames": domain_names}
        
        try:
            print(f"发送请求到 {endpoint}")
            print(f"请求数据: {json.dumps(data, indent=2)}")
            response = self.session.post(endpoint, json=data)
            
            if response.status_code != 200:
                print(f"API 响应错误 - 状态码: {response.status_code}")
                print(f"响应内容: {response.text}")
                
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"请求失败详情: {str(e)}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"错误响应: {e.response.text}")
            raise Exception(f"域名搜索失败: {str(e)}")


    def purchase_domain(self, domain_name: str, years: int = 1, **kwargs) -> Dict[str, Any]:
        """购买域名"""
        endpoint = f"{self.api_url}/domains"
        data = {
            "domain_name": domain_name,
            "years": years,
            **kwargs
        }
        
        try:
            print(f"正在购买域名: {domain_name}")
            response = self.session.post(endpoint, json=data)
            response_json = response.json()
            print(f"购买响应: {json.dumps(response_json, indent=2)}")
            return response_json
        except requests.exceptions.RequestException as e:
            error_msg = f"域名购买失败: {str(e)}"
            print(error_msg)
            if hasattr(e, 'response') and e.response is not None:
                print(f"错误响应: {e.response.text}")
            return {
                'success': False,
                'message': error_msg
            }

    def create_record(self, domain_name: str, record_type: str, host: str, 
                     answer: str, ttl: int = 300) -> Dict[str, Any]:
        """
        创建DNS记录
        """
        endpoint = f"{self.api_url}/domains/{domain_name}/records"
        data = {
            "type": record_type,
            "host": host,
            "answer": answer,
            "ttl": ttl
        }
        
        try:
            response = self.session.post(endpoint, json=data)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            raise Exception(f"创建DNS记录失败: {str(e)}")


def validate_ip(ip: str) -> bool:
    """验证IP地址格式"""
    pattern = r'^(\d{1,3}\.){3}\d{1,3}$'
    if not re.match(pattern, ip): return False
    return all(0 <= int(x) <= 255 for x in ip.split('.'))


def interactive_domain_purchase(username: str, token: str, engine = engine, chat_id: str = None, telegram_token: str = None):
    """交互式域名购买程序"""
    try:
        api = NameComAPI(username=username, token=token)
    except Exception as e:
        print(f"API 初始化失败: {str(e)}")
        return

    while True:
        domain_name = input("\n请输入想要注册的域名（包含后缀，如 example.com）: ").strip().lower()
        if not domain_name:
            print("域名不能为空，请重新输入")
            continue
        if '.' not in domain_name:
            print("请输入完整的域名，包含后缀（如 .com, .ai 等）")
            continue
        
        # 检查域名状态
        status = api.check_domain_status(domain_name)
        print(f"\n域名状态: {status['message']}")
        
        if status['available']:
            while True:
                confirm = input(f"\n是否要购买此域名? (y/n): ").lower()
                if confirm in ['y', 'n']:
                    break
                print("请输入 y 或 n")
            
            if confirm == 'y':
                try:
                    # 执行购买
                    purchase_result = api.purchase_domain(domain_name=domain_name, years=1)
                    if not purchase_result.get('success', False):
                        print(f"\n购买失败: {purchase_result.get('message', '未知错误')}")
                        continue

                    print("\n域名购买成功！")
                    
                    # 询问是否设置 DNS A 记录
                    while True:
                        setup_dns = input(f"\n是否将域名 DNS A 记录指向主服务器 IP ({PRIMARY_INSTANCE_IP_ADDRESS})? (y/n): ").lower()
                        if setup_dns in ['y', 'n']:
                            break
                        print("请输入 y 或 n")
                    
                    if setup_dns == 'y':
                        try:
                            # 设置 A 记录
                            record_result = api.create_record(
                                domain_name=domain_name,
                                record_type="A",
                                host="@",  # @ 表示根域名
                                answer=PRIMARY_INSTANCE_IP_ADDRESS
                            )
                            print(f"\nDNS A 记录设置成功！域名 {domain_name} 已指向 {PRIMARY_INSTANCE_IP_ADDRESS}")

                            record_domain_purchase(chat_id, domain_name, purchase_result, record_result, engine, telegram_token)
                            print("域名购买记录已保存到数据库")

                        except Exception as e:
                            print(f"\nDNS 记录设置失败: {str(e)}")
                            print("请稍后在域名控制面板中手动设置 DNS 记录")

                except Exception as e:
                    print(f"\n域名购买失败: {str(e)}")
                    print("请稍后在域名控制面板中手动购买域名")
            else:
                print("\n取消购买")
        
        retry = input("\n是否继续查询其他域名? (y/n): ").lower()
        if retry != 'y':
            break


def record_domain_purchase(chat_id: int, domain_name: str, purchase_result: dict, dns_record: dict = None, engine = engine, telegram_token: str = TELEGRAM_BOT_TOKEN) -> None:
    """
    记录域名购买信息到数据库
    
    Args:
        engine: SQLAlchemy engine
        chat_id: Telegram 用户的 chat_id
        domain_name: 购买的域名
        purchase_result: 域名购买 API 返回结果
        dns_record: DNS记录设置的返回结果（可选）
    """
    try:
        # 从API响应中提取信息
        expiration_date = purchase_result.get('expire_date')  # 域名到期日期
        registration_date = purchase_result.get('create_date')  # 域名注册日期
        domain_id = purchase_result.get('domain_id')  # Name.com的域名ID
        purchase_price = purchase_result.get('purchase_price')  # 购买价格
        auto_renew = purchase_result.get('auto_renew', False)  # 自动续费状态
        nameservers = ','.join(purchase_result.get('nameservers', []))  # 域名服务器
        
        # 准备插入数据库的记录
        record = {
            'chat_id': chat_id,
            'domain_name': domain_name,
            'domain_id': domain_id,
            'registration_date': registration_date,
            'expiration_date': expiration_date,
            'purchase_price': purchase_price,
            'auto_renew': auto_renew,
            'nameservers': nameservers,
            'dns_a_record': PRIMARY_INSTANCE_IP_ADDRESS if dns_record else None,
            'dns_setup_date': datetime.now() if dns_record else None,
            'registrar': 'name.com',
            'status': 'active',
            'created_at': datetime.now(),
            'last_check_date': datetime.now(),
            'next_renewal_notification_date': (
                datetime.fromisoformat(expiration_date) - timedelta(days=30)
                if expiration_date else None
            )
        }
        
        # 插入数据库
        with engine.begin() as conn:
            conn.execute(
                text("""
                    INSERT INTO domain_name_record (
                        chat_id, domain_name, domain_id, registration_date,
                        expiration_date, purchase_price, auto_renew, nameservers,
                        dns_a_record, dns_setup_date, registrar, status,
                        created_at, last_check_date, next_renewal_notification_date
                    ) VALUES (
                        :chat_id, :domain_name, :domain_id, :registration_date,
                        :expiration_date, :purchase_price, :auto_renew, :nameservers,
                        :dns_a_record, :dns_setup_date, :registrar, :status,
                        :created_at, :last_check_date, :next_renewal_notification_date
                    )
                """),
                record
            )
            
        print(f"\n域名购买记录已保存到数据库")

        ghost_api_url = f"https://{domain_name}" if not domain_name.startswith('https://') else domain_name

        set_ghost_blog_url(chat_id, ghost_api_url, telegram_token, engine)
        
    except Exception as e:
        print(f"\n保存域名购买记录失败: {str(e)}")


def setup_domain_verification(api: NameComAPI, domain_name: str, txt_name: str, txt_value: str) -> bool:
    """
    Set up domain verification by adding a TXT record
    
    Args:
        api: Initialized NameComAPI instance
        domain_name: Domain name to verify
        txt_name: Name/host of TXT record (e.g., "@" or specific subdomain)
        txt_value: Value for TXT record (verification string provided by Google)
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Create TXT record
        record_result = api.create_record(
            domain_name=domain_name,
            record_type="TXT",
            host=txt_name,  # Usually "@" for root domain
            answer=txt_value,
            ttl=3600  # 1 hour TTL is usually sufficient for verification
        )
        
        print(f"\nTXT record created successfully:")
        print(f"Domain: {domain_name}")
        print(f"Name/Host: {txt_name}")
        print(f"Value: {txt_value}")
        print("\nPlease note:")
        print("1. DNS changes may take up to 48 hours to propagate")
        print("2. For Google Search Console, you can attempt verification after a few minutes")
        print("3. The TXT record will remain unless manually removed")
        
        return f"TXT record created successfully for domain {domain_name}"
        
    except Exception as e: return e

# Example usage
def verify_google_search_console(api: NameComAPI, domain_name: str, verification_string: str) -> bool:
    """
    Specific function for Google Search Console verification
    
    Args:
        api: Initialized NameComAPI instance
        domain_name: Domain to verify
        verification_string: Google's verification string
        
    Returns:
        bool: True if successful, False otherwise
    """
    # For Google Search Console, we typically use "@" as the host
    return setup_domain_verification(
        api=api,
        domain_name=domain_name,
        txt_name="@",
        txt_value=verification_string
    )


# Interactive usage example
def domain_verification(domain_name:str, verification_string:str, username: str=DOMAIN_NAME_USERNAME, token: str=DOMAIN_NAME_TOKEN):
    """Interactive function for domain verification"""
    try: api = NameComAPI(username=username, token=token)
    except Exception as e: return f"API initialization failed: {str(e)}"

    return verify_google_search_console(api, domain_name, verification_string)

def update_subdomain_a_record(api: NameComAPI, domain_name: str, subdomain: str, new_ip: str, ttl: int = 300) -> Dict[str, Any]:
    """
    更新域名的二级域名 A 记录

    Args:
        api (NameComAPI): 已初始化的 NameComAPI 客户端
        domain_name (str): 主域名，例如 "example.com"
        subdomain (str): 二级域名，例如 "www" 或 "blog"
        new_ip (str): 新的 IP 地址
        ttl (int, optional): TTL 值（默认 300 秒）

    Returns:
        Dict[str, Any]: 返回更新结果
    """
    if not validate_ip(new_ip):
        return {"success": False, "message": "无效的 IP 地址"}

    try:
        print(f"正在更新 {domain_name} 的二级域名 {subdomain} 的 A 记录，指向 IP: {new_ip}")

        # 查询现有 DNS 记录
        records_response = api.session.get(f"{api.api_url}/domains/{domain_name}/records")
        records_response.raise_for_status()
        records = records_response.json().get("records", [])

        print("现有 DNS 记录:", json.dumps(records, indent=2))


        # 查找现有记录（确保字段存在）
        existing_record = next(
            (
                record
                for record in records
                if record.get("type") == "A" and record.get("host") == subdomain
            ),
            None,
        )

        if existing_record:
            # 更新现有记录
            record_id = existing_record["id"]
            update_response = api.session.put(
                f"{api.api_url}/domains/{domain_name}/records/{record_id}",
                json={"type": "A", "host": subdomain, "answer": new_ip, "ttl": ttl},
            )
            update_response.raise_for_status()
            return {"success": True, "message": f"二级域名 {subdomain}.{domain_name} 的 A 记录已更新为 {new_ip}"}
        else:
            # 创建新记录
            create_response = api.create_record(
                domain_name=domain_name,
                record_type="A",
                host=subdomain,
                answer=new_ip,
                ttl=ttl,
            )
            return {"success": True, "message": f"二级域名 {subdomain}.{domain_name} 的 A 记录已创建，指向 {new_ip}"}
    except requests.exceptions.RequestException as e:
        error_msg = f"操作失败: {str(e)}"
        print(error_msg)
        if hasattr(e, "response") and e.response is not None:
            print(f"错误响应: {e.response.text}")
        return {"success": False, "message": error_msg}


if __name__ == "__main__":
    username = DOMAIN_NAME_USERNAME  # 替换为你的 Name.com 用户名
    token = DOMAIN_NAME_TOKEN        # 替换为你的 API Token
    # api = NameComAPI(username, token)

    # domain_name = input("请输入主域名（例如 example.com）: ").strip()
    # subdomain = input("请输入需要更新的二级域名（例如 www 或 blog）: ").strip()
    # new_ip = input("请输入新的 IP 地址: ").strip()

    # result = update_subdomain_a_record(api, domain_name, subdomain, new_ip)
    # print(f"结果: {result['message']}")
