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


def send_verification_email(recipient_email: str, verification_code: str, server_url: str = None) -> bool:
    """
    发送验证码邮件
    
    Args:
        recipient_email: 收件人邮箱
        verification_code: 验证码
        server_url: 服务器地址(可选),如果提供则在邮件中包含验证链接
        
    Returns:
        bool: 发送是否成功
    """
    
    # 检查配置
    if not EMAIL_PASSWORD:
        logger.error("邮箱授权码未配置，请在 config.py 中设置 EMAIL_PASSWORD")
        return False
    
    try:
        # 构建邮件内容
        html_content = build_verification_email_template(verification_code, recipient_email, server_url)
        
        # 创建邮件对象
        message = MIMEMultipart('alternative')
        message['From'] = EMAIL_SENDER
        message['To'] = recipient_email
        message['Subject'] = Header("Registration Verification Code - Please Verify Your Email", 'utf-8')
        
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


def build_verification_email_template(verification_code: str, recipient_email: str, server_url: str = None) -> str:
    """
    构建验证码邮件模板
    
    Args:
        verification_code: 验证码
        recipient_email: 收件人邮箱
        server_url: 服务器地址(可选)
    """
    
    # 构建验证链接
    from urllib.parse import quote
    verification_link = ""
    if server_url:
        verification_link = f"{server_url}/verify?email={quote(recipient_email)}"
    
    # 如果有链接,添加按钮区域
    link_section = ""
    if verification_link:
        link_section = f"""
        <div class="info">
            <p style="text-align: center; margin: 20px 0;">
                <a href="{verification_link}" 
                   style="display: inline-block; 
                          background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                          color: white;
                          padding: 12px 30px;
                          border-radius: 8px;
                          text-decoration: none;
                          font-weight: 600;
                          font-size: 16px;">
                    🔗 Open Verification Page
                </a>
            </p>
            <p style="text-align: center; color: #7f8c8d; font-size: 12px;">
                Or copy this link: <br>
                <a href="{verification_link}" style="color: #3498db; word-break: break-all;">{verification_link}</a>
            </p>
        </div>
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
            <h1>Email Verification</h1>
        </div>
        
        <div class="info">
            <p>Thank you for registering <strong>{SYSTEM_NAME}</strong>!</p>
            <p>Please use the following verification code to complete your registration:</p>
        </div>
        
        <div class="code-section">
            <div class="code">{verification_code}</div>
            <div class="code-label">Verification Code</div>
        </div>
        
        {link_section}
        
        <div class="warning">
            <p>⏰ <strong>Code expires in: 10 minutes</strong></p>
            <p>🔒 Do not share this code with anyone</p>
            <p>❓ If this was not you, please ignore this email</p>
        </div>
        
        <div class="footer">
            <p>If you have any questions, please contact: <a href="mailto:{CONTACT_EMAIL}">{CONTACT_EMAIL}</a></p>
            <p style="margin-top: 15px; font-size: 12px; color: #95a5a6;">
                This email was automatically sent by {SYSTEM_NAME}, please do not reply
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
        leader_badge = "👑 Leader" if member.get("isLeader", False) else "Member"
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
            <h1>Congratulations for successfully registering for the CSV Challenge (ISBI2026)!</h1>
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
                <div class="label">Team Members ({len(members)} members)</div>
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
