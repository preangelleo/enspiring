from tg_operation import *
from playwright.sync_api import sync_playwright
import os

def html_to_image(url: str, output_path: str):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={'width': 1920, 'height': 1080})  # 设置视窗大小
        page.goto(url)
        
        # 等待页面加载完成（可选）
        page.wait_for_load_state('networkidle')
        
        # 截取整个页面，包括滚动部分
        page.screenshot(
            path=output_path,
            full_page=True  # 这是关键设置
        )
        browser.close()


def html_file_to_image(html_path: str, output_path: str):
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={'width': 1920, 'height': 1080})
        
        # 使用绝对路径和 file:// 协议
        abs_path = os.path.abspath(html_path)
        page.goto(f'file://{abs_path}')
        
        # 等待页面加载完成
        page.wait_for_load_state('domcontentloaded')
        
        # 截取整个页面，包括滚动部分
        page.screenshot(
            path=output_path,
            full_page=True
        )
        browser.close()
    send_document_from_file(OWNER_CHAT_ID, output_path, 'Screenshot', os.getenv('TELEGRAM_BOT_TOKEN_TEST'))


if __name__ == '__main__':
    # 使用示例
    file_path = 'Temp/website.jpg'
    html_to_image('https://gmora.ai/bp6krka6yry/', 'Temp/website.jpg')
    send_document_from_file(OWNER_CHAT_ID, file_path, 'Screenshot', os.getenv('TELEGRAM_BOT_TOKEN_TEST'))
    
    # html_file_to_image('page.html', 'Images/local.jpg')
