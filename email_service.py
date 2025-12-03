import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import Header
from typing import List, Dict
import logging
import random
import string

# 导入配置
from config import (
    SMTP_HOST, SMTP_PORT, USE_SSL,
    EMAIL_SENDER, EMAIL_PASSWORD,
    EMAIL_FROM_NAME, EMAIL_SUBJECT,
    SYSTEM_NAME, CONTACT_EMAIL
)

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def generate_verification_code(length=6) -> str:
    """
    生成随机验证码
    
    Args:
        length: 验证码长度，默认6位
        
    Returns:
        str: 验证码
    """
    return ''.join(random.choices(string.digits, k=length))


def send_verification_email(recipient_email: str, verification_code: str) -> bool:
    """
    发送验证码邮件
    
    Args:
        recipient_email: 收件人邮箱
        verification_code: 验证码
        
    Returns:
        bool: 发送是否成功
    """
    
    # 检查配置
    if not EMAIL_PASSWORD:
        logger.error("邮箱授权码未配置，请在 config.py 中设置 EMAIL_PASSWORD")
        return False
    
    try:
        # 构建邮件内容
        html_content = build_verification_email_template(verification_code)
        
        # 创建邮件对象
        message = MIMEMultipart('alternative')
        message['From'] = EMAIL_SENDER
        message['To'] = recipient_email
        message['Subject'] = Header("注册验证码 - 请验证您的邮箱", 'utf-8')
        
        # 添加HTML内容
        html_part = MIMEText(html_content, 'html', 'utf-8')
        message.attach(html_part)
        
        # 连接SMTP服务器并发送
        if USE_SSL:
            server = smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT)
        else:
            server = smtplib.SMTP(SMTP_HOST, SMTP_PORT)
            server.starttls()
        
        # 登录
        server.login(EMAIL_SENDER, EMAIL_PASSWORD)
        
        # 发送邮件
        server.sendmail(EMAIL_SENDER, recipient_email, message.as_string())
        server.quit()
        
        logger.info(f"验证码邮件已发送至: {recipient_email}")
        return True
        
    except smtplib.SMTPAuthenticationError:
        logger.error("邮箱认证失败，请检查邮箱地址和授权码是否正确")
        return False
    except smtplib.SMTPException as e:
        logger.error(f"SMTP错误: {str(e)}")
        return False
    except Exception as e:
        logger.error(f"发送邮件失败: {str(e)}")
        return False


def build_verification_email_template(verification_code: str) -> str:
    """
    构建验证码邮件模板
    """
    
    html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 600px;
            margin: 0 auto;
            padding: 20px;
        }}
        .container {{
            background-color: #f9f9f9;
            border-radius: 8px;
            padding: 30px;
            border: 1px solid #e0e0e0;
        }}
        .header {{
            text-align: center;
            margin-bottom: 30px;
        }}
        .header h1 {{
            color: #2c3e50;
            margin: 0;
            font-size: 24px;
        }}
        .icon {{
            font-size: 48px;
            margin-bottom: 10px;
        }}
        .code-section {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 30px;
            border-radius: 10px;
            text-align: center;
            margin: 30px 0;
        }}
        .code {{
            color: white;
            font-size: 36px;
            font-weight: bold;
            letter-spacing: 8px;
            font-family: 'Courier New', monospace;
        }}
        .code-label {{
            color: rgba(255, 255, 255, 0.9);
            font-size: 14px;
            margin-top: 10px;
        }}
        .info {{
            background-color: white;
            padding: 20px;
            border-radius: 6px;
            margin: 20px 0;
        }}
        .info p {{
            margin: 10px 0;
            color: #555;
        }}
        .warning {{
            background-color: #fff3cd;
            border-left: 4px solid #ffc107;
            padding: 15px;
            margin: 20px 0;
            border-radius: 4px;
        }}
        .warning p {{
            margin: 5px 0;
            color: #856404;
            font-size: 14px;
        }}
        .footer {{
            text-align: center;
            margin-top: 30px;
            padding-top: 20px;
            border-top: 1px solid #e0e0e0;
            color: #7f8c8d;
            font-size: 14px;
        }}
        .footer a {{
            color: #3498db;
            text-decoration: none;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div class="icon">✉️</div>
            <h1>邮箱验证</h1>
        </div>
        
        <div class="info">
            <p>感谢您注册 <strong>{SYSTEM_NAME}</strong>！</p>
            <p>请使用以下验证码完成注册：</p>
        </div>
        
        <div class="code-section">
            <div class="code">{verification_code}</div>
            <div class="code-label">验证码</div>
        </div>
        
        <div class="warning">
            <p>⏰ <strong>验证码有效期：10分钟</strong></p>
            <p>🔒 请勿将验证码告知他人</p>
            <p>❓ 如果这不是您的操作，请忽略此邮件</p>
        </div>
        
        <div class="footer">
            <p>如有疑问，请联系：<a href="mailto:{CONTACT_EMAIL}">{CONTACT_EMAIL}</a></p>
            <p style="margin-top: 15px; font-size: 12px; color: #95a5a6;">
                此邮件由 {SYSTEM_NAME} 自动发送，请勿直接回复
            </p>
        </div>
    </div>
</body>
</html>
"""
    
    return html


def send_confirmation_email(
    recipient_email: str,
    team_name: str,
    username: str,
    organization: str,
    members: List[Dict[str, any]]
) -> bool:
    """
    发送注册确认邮件
    
    Args:
        recipient_email: 收件人邮箱
        team_name: 团队名称
        username: 用户名
        organization: 组织/单位
        members: 团队成员列表
        
    Returns:
        bool: 发送是否成功
    """
    
    # 检查配置
    if not EMAIL_PASSWORD:
        logger.error("邮箱授权码未配置，请在 config.py 中设置 EMAIL_PASSWORD")
        return False
    
    try:
        # 构建邮件内容
        html_content = build_email_template(
            team_name=team_name,
            username=username,
            organization=organization,
            members=members
        )
        
        # 创建邮件对象
        message = MIMEMultipart('alternative')
        message['From'] = EMAIL_SENDER  # QQ邮箱要求From必须是纯邮箱地址
        message['To'] = recipient_email
        message['Subject'] = Header(EMAIL_SUBJECT, 'utf-8')
        
        # 添加HTML内容
        html_part = MIMEText(html_content, 'html', 'utf-8')
        message.attach(html_part)
        
        # 连接SMTP服务器并发送
        if USE_SSL:
            # 使用SSL加密连接
            server = smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT)
        else:
            # 使用TLS加密连接
            server = smtplib.SMTP(SMTP_HOST, SMTP_PORT)
            server.starttls()
        
        # 登录
        server.login(EMAIL_SENDER, EMAIL_PASSWORD)
        
        # 发送邮件
        server.sendmail(EMAIL_SENDER, recipient_email, message.as_string())
        server.quit()
        
        logger.info(f"确认邮件已发送至: {recipient_email}")
        return True
        
    except smtplib.SMTPAuthenticationError:
        logger.error("邮箱认证失败，请检查邮箱地址和授权码是否正确")
        return False
    except smtplib.SMTPException as e:
        logger.error(f"SMTP错误: {str(e)}")
        return False
    except Exception as e:
        logger.error(f"发送邮件失败: {str(e)}")
        return False


def build_email_template(
    team_name: str,
    username: str,
    organization: str,
    members: List[Dict[str, any]]
) -> str:
    """
    构建简洁的HTML邮件模板
    """
    
    # 构建成员列表HTML
    members_html = ""
    for member in members:
        leader_badge = "👑 队长" if member.get("isLeader", False) else "成员"
        members_html += f"<li>{member['name']} ({leader_badge})</li>\n"
    
    # HTML模板
    html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 600px;
            margin: 0 auto;
            padding: 20px;
        }}
        .container {{
            background-color: #f9f9f9;
            border-radius: 8px;
            padding: 30px;
            border: 1px solid #e0e0e0;
        }}
        .header {{
            text-align: center;
            margin-bottom: 30px;
        }}
        .header h1 {{
            color: #2c3e50;
            margin: 0;
            font-size: 24px;
        }}
        .success-icon {{
            font-size: 48px;
            margin-bottom: 10px;
        }}
        .info-section {{
            background-color: white;
            padding: 20px;
            border-radius: 6px;
            margin-bottom: 20px;
        }}
        .info-row {{
            margin-bottom: 12px;
            padding-bottom: 12px;
            border-bottom: 1px solid #f0f0f0;
        }}
        .info-row:last-child {{
            border-bottom: none;
            margin-bottom: 0;
        }}
        .label {{
            color: #7f8c8d;
            font-size: 14px;
            margin-bottom: 4px;
        }}
        .value {{
            color: #2c3e50;
            font-size: 16px;
            font-weight: 500;
        }}
        .members-list {{
            list-style-type: none;
            padding-left: 0;
            margin: 10px 0 0 0;
        }}
        .members-list li {{
            padding: 6px 0;
            color: #34495e;
        }}
        .footer {{
            text-align: center;
            margin-top: 30px;
            padding-top: 20px;
            border-top: 1px solid #e0e0e0;
            color: #7f8c8d;
            font-size: 14px;
        }}
        .footer a {{
            color: #3498db;
            text-decoration: none;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div class="success-icon">✅</div>
            <h1>Congratulations for successfully registering for theCSV Challenge (ISBI2026)!</h1>
        </div>
        
        <div class="info-section">
            <div class="info-row">
                <div class="label">Team Name</div>
                <div class="value">{team_name}</div>
            </div>
            
            <div class="info-row">
                <div class="label">Organization</div>
                <div class="value">{organization}</div>
            </div>
            
            <div class="info-row">
                <div class="label">Username</div>
                <div class="value">{username}</div>
            </div>
            
            <div class="info-row">
                <div class="label">Team Members ({len(members)}人)</div>
                <ul class="members-list">
                    {members_html}
                </ul>
            </div>
        </div>
        
        <div class="footer">
            <p>This is an automatically generated email. Please do not reply to this email.</p>
            <p>If you have any questions, please contact us at <a href="mailto:{CONTACT_EMAIL}">{CONTACT_EMAIL}</a></p>
        </div>
    </div>
</body>
</html>
"""
    
    return html
