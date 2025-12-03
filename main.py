from fastapi import FastAPI, HTTPException, Depends, status, Request, Response
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from pydantic import BaseModel, EmailStr
from typing import List, Optional
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import secrets
import uuid

# 导入数据库相关
from database import init_db, get_db, TeamRegistration, TeamMember, VerificationCode, Submission

# 导入邮件服务
from email_service import send_verification_email, generate_verification_code

# 导入配置
from config import DOCS_USERNAME, DOCS_PASSWORD

# 存储一次性访问token (实际生产环境应使用Redis等缓存)
# 格式: {token: {"username": str, "expires": datetime}}
docs_tokens = {}

# HTTP Basic 认证
security = HTTPBasic(auto_error=False)

def verify_docs_credentials(credentials: HTTPBasicCredentials = Depends(security)):
    """验证文档访问凭证并生成一次性token"""
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="文档访问需要认证",
            headers={"WWW-Authenticate": 'Basic realm="API Documentation"'},
        )
    
    correct_username = secrets.compare_digest(credentials.username, DOCS_USERNAME)
    correct_password = secrets.compare_digest(credentials.password, DOCS_PASSWORD)
    
    if not (correct_username and correct_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
            headers={"WWW-Authenticate": 'Basic realm="API Documentation"'},
        )
    
    return credentials.username

def verify_docs_token(request: Request):
    """验证一次性访问token"""
    token = request.query_params.get("token")
    
    if not token or token not in docs_tokens:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="未授权访问或token已失效，请重新认证",
        )
    
    # 验证token是否过期 (这里设置为立即失效,仅允许一次使用)
    token_data = docs_tokens.get(token)
    if datetime.utcnow() > token_data["expires"]:
        del docs_tokens[token]
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token已过期，请重新认证",
        )
    
    return token_data["username"]

# 创建FastAPI应用实例（文档路由需要认证）
app = FastAPI(
    docs_url=None,  # 禁用默认的 /docs
    redoc_url=None,  # 禁用默认的 /redoc
)

# 初始化数据库
@app.on_event("startup")
async def startup_event():
    init_db()
    print("数据库初始化完成")

# 受保护的文档路由
from fastapi.openapi.docs import get_swagger_ui_html, get_redoc_html
from fastapi.openapi.utils import get_openapi

@app.get("/docs-auth", include_in_schema=False)
async def docs_auth(username: str = Depends(verify_docs_credentials)):
    """文档认证入口 - 验证成功后生成一次性token并重定向"""
    # 生成一次性token
    token = str(uuid.uuid4())
    
    # 清理过期的token
    global docs_tokens
    docs_tokens = {k: v for k, v in docs_tokens.items() if datetime.utcnow() <= v["expires"]}
    
    # 保存token (设置5秒过期,只够加载一次页面)
    docs_tokens[token] = {
        "username": username,
        "expires": datetime.utcnow() + timedelta(seconds=5)
    }
    
    # 重定向到实际的文档页面,带上一次性token
    return RedirectResponse(url=f"/docs?token={token}", status_code=302)

@app.get("/docs", include_in_schema=False)
async def get_documentation(request: Request, username: str = Depends(verify_docs_token)):
    """Swagger UI 文档 - 需要一次性token"""
    token = request.query_params.get("token")
    response = get_swagger_ui_html(
        openapi_url=f"/openapi.json?token={token}", 
        title="API文档"
    )
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    return response

@app.get("/redoc-auth", include_in_schema=False)
async def redoc_auth(username: str = Depends(verify_docs_credentials)):
    """ReDoc认证入口 - 验证成功后生成一次性token并重定向"""
    token = str(uuid.uuid4())
    
    global docs_tokens
    docs_tokens = {k: v for k, v in docs_tokens.items() if datetime.utcnow() <= v["expires"]}
    
    docs_tokens[token] = {
        "username": username,
        "expires": datetime.utcnow() + timedelta(seconds=5)
    }
    
    return RedirectResponse(url=f"/redoc?token={token}", status_code=302)

@app.get("/redoc", include_in_schema=False)
async def get_redoc_documentation(request: Request, username: str = Depends(verify_docs_token)):
    """ReDoc 文档 - 需要一次性token"""
    token = request.query_params.get("token")
    response = get_redoc_html(
        openapi_url=f"/openapi.json?token={token}", 
        title="API文档"
    )
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    return response

@app.get("/openapi.json", include_in_schema=False)
async def get_open_api_endpoint(username: str = Depends(verify_docs_token)):
    """OpenAPI schema - 需要一次性token"""
    from fastapi.responses import JSONResponse
    openapi_schema = get_openapi(title="挑战赛API文档", version="1.0.0", routes=app.routes)
    response = JSONResponse(content=openapi_schema)
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    return response

# 根路径测试
@app.get("/")
async def root():
    return {"message": "服务器运行正常", "status": "ok"}

# 定义API数据模型（Pydantic）
class Member(BaseModel):
    name: str
    isLeader: bool = False

class RegistrationData(BaseModel):
    teamName: str
    organization: str
    orgAddress: str = ""
    email: EmailStr
    username: str
    password: str
    members: List[Member]

class VerifyCodeData(BaseModel):
    email: EmailStr
    code: str

class LoginData(BaseModel):
    username: str
    password: str
    rememberMe: bool = False

class SubmissionData(BaseModel):
    username: str
    title: str
    url: str
    description: str = ""

# 响应模型
class MemberResponse(BaseModel):
    name: str
    isLeader: bool
    
    class Config:
        from_attributes = True

class RegistrationResponse(BaseModel):
    teamName: str
    organization: str
    email: str
    username: str
    memberCount: int
    members: List[MemberResponse]
    
    class Config:
        from_attributes = True

# 提供注册页面
@app.get("/register", response_class=HTMLResponse)
async def serve_registration_page():
    with open("register.html", "r", encoding="utf-8") as f:
        return f.read()

# 提供验证码页面
@app.get("/verify", response_class=HTMLResponse)
async def serve_verification_page():
    with open("verify.html", "r", encoding="utf-8") as f:
        return f.read()

# 提供登录页面
@app.get("/login", response_class=HTMLResponse)
async def serve_login_page():
    with open("login.html", "r", encoding="utf-8") as f:
        return f.read()

# 提供个人主页
@app.get("/dashboard", response_class=HTMLResponse)
async def serve_dashboard_page():
    with open("dashboard.html", "r", encoding="utf-8") as f:
        return f.read()

# 第一步：接收注册数据，发送验证码
@app.post("/api/register")
async def register_team(data: RegistrationData, db: Session = Depends(get_db)):
    # 检查用户名是否已存在
    existing_username = db.query(TeamRegistration).filter(
        TeamRegistration.username == data.username
    ).first()
    if existing_username:
        raise HTTPException(status_code=400, detail="用户名已存在")
    
    # 检查邮箱是否已存在
    existing_email = db.query(TeamRegistration).filter(
        TeamRegistration.email == data.email
    ).first()
    if existing_email:
        raise HTTPException(status_code=400, detail="邮箱已被注册")
    
    # 生成验证码
    verification_code = generate_verification_code(6)
    
    # 保存验证码到数据库（有效期10分钟）
    expires_at = datetime.utcnow() + timedelta(minutes=10)
    
    # 删除该邮箱之前的未使用验证码
    db.query(VerificationCode).filter(
        VerificationCode.email == data.email,
        VerificationCode.is_used == False
    ).delete()
    
    db_code = VerificationCode(
        email=data.email,
        code=verification_code,
        expires_at=expires_at
    )
    db.add(db_code)
    
    # 暂存注册信息（未验证状态）
    db_team = TeamRegistration(
        teamName=data.teamName,
        organization=data.organization,
        orgAddress=data.orgAddress,
        email=data.email,
        username=data.username,
        password=data.password,
        is_verified=False  # 标记为未验证
    )
    
    # 添加成员
    for member_data in data.members:
        db_member = TeamMember(
            name=member_data.name,
            isLeader=member_data.isLeader
        )
        db_team.members.append(db_member)
    
    # 保存到数据库
    db.add(db_team)
    db.commit()
    db.refresh(db_code)
    
    # 发送验证码邮件
    try:
        email_sent = send_verification_email(data.email, verification_code)
        
        if email_sent:
            print(f"✅ 验证码已发送至: {data.email}")
        else:
            print(f"⚠️ 验证码发送失败: {data.email}")
            raise HTTPException(status_code=500, detail="验证码发送失败，请稍后重试")
            
    except Exception as e:
        print(f"❌ 邮件发送异常: {str(e)}")
        raise HTTPException(status_code=500, detail="验证码发送失败，请稍后重试")
    
    return {
        "status": "success",
        "message": "验证码已发送到您的邮箱，请查收",
        "data": {
            "email": data.email,
            "expiresIn": 600  # 10分钟 = 600秒
        }
    }

# 第二步：验证验证码，完成注册
@app.post("/api/verify")
async def verify_code(data: VerifyCodeData, db: Session = Depends(get_db)):
    # 查找验证码
    db_code = db.query(VerificationCode).filter(
        VerificationCode.email == data.email,
        VerificationCode.code == data.code,
        VerificationCode.is_used == False
    ).first()
    
    if not db_code:
        raise HTTPException(status_code=400, detail="验证码错误或已失效")
    
    # 检查是否过期
    if datetime.utcnow() > db_code.expires_at:
        raise HTTPException(status_code=400, detail="验证码已过期，请重新注册")
    
    # 查找对应的注册信息
    db_team = db.query(TeamRegistration).filter(
        TeamRegistration.email == data.email,
        TeamRegistration.is_verified == False
    ).first()
    
    if not db_team:
        raise HTTPException(status_code=404, detail="未找到待验证的注册信息")
    
    # 标记验证码为已使用
    db_code.is_used = True
    
    # 标记注册信息为已验证
    db_team.is_verified = True
    
    db.commit()
    db.refresh(db_team)
    
    return {
        "status": "success",
        "message": "注册成功！",
        "data": {
            "teamName": db_team.teamName,
            "username": db_team.username,
            "email": db_team.email,
            "memberCount": len(db_team.members)
        }
    }

# 登录API
@app.post("/api/login")
async def login_user(data: LoginData, db: Session = Depends(get_db)):
    # 查找用户（支持用户名或邮箱登录）
    user = db.query(TeamRegistration).filter(
        (TeamRegistration.username == data.username) | (TeamRegistration.email == data.username)
    ).first()
    
    if not user:
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    
    # 检查用户是否已验证邮箱
    if not user.is_verified:
        raise HTTPException(status_code=403, detail="账户尚未验证，请先完成邮箱验证")
    
    # 验证密码（实际应用中应该使用哈希比对）
    if user.password != data.password:
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    
    # 生成简单的token（实际应用中应该使用JWT）
    token = secrets.token_urlsafe(32)
    
    return {
        "status": "success",
        "message": "登录成功",
        "data": {
            "username": user.username,
            "teamName": user.teamName,
            "email": user.email,
            "organization": user.organization
        },
        "token": token
    }

# 获取所有注册信息（管理接口） - 只显示已验证的
@app.get("/get/registrations/all", response_model=dict)
async def get_registrations(db: Session = Depends(get_db)):
    registrations = db.query(TeamRegistration).filter(
        TeamRegistration.is_verified == True
    ).all()
    
    return {
        "total": len(registrations),
        "data": [
            {
                "teamName": reg.teamName,
                "organization": reg.organization,
                "email": reg.email,
                "username": reg.username,
                "memberCount": len(reg.members),
                "members": [
                    {
                        "name": m.name,
                        "isLeader": m.isLeader
                    }
                    for m in reg.members
                ]
            }
            for reg in registrations
        ]
    }

# 使用用户名删除接口
@app.delete("/delete/member/{username}")
async def delete_registration(username: str, db: Session = Depends(get_db)):
    registration = db.query(TeamRegistration).filter(
        TeamRegistration.username == username
    ).first()
    
    if not registration:
        raise HTTPException(status_code=404, detail="用户名不存在")
    
    db.delete(registration)
    db.commit()
    
    return {
        "status": "success", 
        "message": f"用户 {username} 的注册信息已删除"
    }

# 获取团队成员信息
@app.get("/api/team/{username}/members")
async def get_team_members(username: str, db: Session = Depends(get_db)):
    team = db.query(TeamRegistration).filter(
        TeamRegistration.username == username,
        TeamRegistration.is_verified == True
    ).first()
    
    if not team:
        raise HTTPException(status_code=404, detail="团队不存在")
    
    return {
        "status": "success",
        "data": [
            {
                "name": member.name,
                "isLeader": member.isLeader
            }
            for member in team.members
        ]
    }

# 提交作品链接
@app.post("/api/submission")
async def submit_work(data: SubmissionData, db: Session = Depends(get_db)):
    # 验证用户是否存在
    user = db.query(TeamRegistration).filter(
        TeamRegistration.username == data.username,
        TeamRegistration.is_verified == True
    ).first()
    
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在或未验证")
    
    # 创建提交记录
    submission = Submission(
        username=data.username,
        title=data.title,
        url=data.url,
        description=data.description
    )
    
    db.add(submission)
    db.commit()
    db.refresh(submission)
    
    return {
        "status": "success",
        "message": "作品提交成功",
        "data": {
            "id": submission.id,
            "title": submission.title,
            "url": submission.url,
            "created_at": submission.created_at.isoformat()
        }
    }

# 获取用户的提交历史
@app.get("/api/submission/{username}")
async def get_submissions(username: str, db: Session = Depends(get_db)):
    # 验证用户是否存在
    user = db.query(TeamRegistration).filter(
        TeamRegistration.username == username,
        TeamRegistration.is_verified == True
    ).first()
    
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    # 获取该用户的所有提交记录，按时间倒序
    submissions = db.query(Submission).filter(
        Submission.username == username
    ).order_by(Submission.created_at.desc()).all()
    
    return {
        "status": "success",
        "data": [
            {
                "id": sub.id,
                "title": sub.title,
                "url": sub.url,
                "description": sub.description,
                "created_at": sub.created_at.isoformat()
            }
            for sub in submissions
        ]
    }

# 获取所有提交记录（管理接口）
@app.get("/api/submissions/all")
async def get_all_submissions(db: Session = Depends(get_db)):
    submissions = db.query(Submission).order_by(Submission.created_at.desc()).all()
    
    return {
        "status": "success",
        "total": len(submissions),
        "data": [
            {
                "id": sub.id,
                "username": sub.username,
                "title": sub.title,
                "url": sub.url,
                "description": sub.description,
                "created_at": sub.created_at.isoformat()
            }
            for sub in submissions
        ]
    }
