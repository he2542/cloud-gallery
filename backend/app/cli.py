import argparse
import getpass
from sqlalchemy import select
from app.core.database import SessionLocal, init_db
from app.core.security import hash_password
from app.models import Space, User
from app.schemas import Credentials

def main():
    parser = argparse.ArgumentParser(description='云图库维护命令')
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('init-db')
    sub.add_parser('seed-demo')
    sub.add_parser('clear-demo')
    sub.add_parser('create-user').add_argument('username')
    args = parser.parse_args()
    if args.command in {'seed-demo', 'clear-demo'}:
        from app.demo import seed, clear
        (seed if args.command == 'seed-demo' else clear)()
        return
    if args.command == 'init-db':
        init_db()
        print('数据库初始化完成')
        return
    password = getpass.getpass('登录密码（至少 10 个字符）：')
    if password != getpass.getpass('再次输入：'):
        raise SystemExit('两次输入不一致')
    c = Credentials(username=args.username, password=password)
    with SessionLocal() as db:
        if db.scalar(select(User).where(User.username == c.username)):
            raise SystemExit('该用户已存在')
        user = User(username=c.username, password_hash=hash_password(password))
        db.add(user)
        db.flush()
        db.add(Space(name='我的私有空间', owner_id=user.id, is_public=False))
        db.commit()
    print('账户创建完成')

if __name__ == '__main__':
    main()
