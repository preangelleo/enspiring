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


if __name__ == "__main__":
    chat_id = OWNER_CHAT_ID
    username = DOMAIN_NAME_USERNAME
    token = DOMAIN_NAME_TOKEN
    telegram_token = TELEGRAM_BOT_TOKEN
    interactive_domain_purchase(username, token, engine, chat_id, telegram_token)