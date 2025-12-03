from fastapi import FastAPI, HTTPException, Depends
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, EmailStr
from typing import List, Optional
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import secrets

# 导入数据库相关
from database import init_db, get_db, TeamRegistration, TeamMember, VerificationCode

# 导入邮件服务
from email_service import send_verification_email, generate_verification_code

# 创建FastAPI应用实例
app = FastAPI()

# 初始化数据库
@app.on_event("startup")
async def startup_event():
    init_db()
    print("数据库初始化完成")

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
