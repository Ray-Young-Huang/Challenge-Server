from fastapi import FastAPI, HTTPException, Depends
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, EmailStr
from typing import List
from sqlalchemy.orm import Session

# 导入数据库相关
from database import init_db, get_db, TeamRegistration, TeamMember

# 创建FastAPI应用实例
app = FastAPI()

# 初始化数据库
@app.on_event("startup")
async def startup_event():
    init_db()
    print("数据库初始化完成")

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

# 接收注册数据
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
    
    # 创建团队注册记录
    db_team = TeamRegistration(
        teamName=data.teamName,
        organization=data.organization,
        orgAddress=data.orgAddress,
        email=data.email,
        username=data.username,
        password=data.password  # 注意：实际应用中应该使用密码哈希
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
    db.refresh(db_team)
    
    return {
        "status": "success",
        "message": "注册成功！",
        "data": {
            "teamName": db_team.teamName,
            "username": db_team.username,
            "memberCount": len(db_team.members)
        }
    }

# 获取所有注册信息（管理接口）
@app.get("/get/registrations/all", response_model=dict)
async def get_registrations(db: Session = Depends(get_db)):
    registrations = db.query(TeamRegistration).all()
    
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
