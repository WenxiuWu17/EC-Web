from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # 用於保持 session 安全

# 配置資料庫
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///ecommerce.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# 初始化 SQLAlchemy 和 LoginManager
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'  # 指定未登入時的重定向頁面為 'login'

# 賣家資料模型
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

# 商品資料模型
class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    price = db.Column(db.Integer, nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    seller_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    seller = db.relationship('User', backref=db.backref('products', lazy=True))

# 初始化資料庫（僅需執行一次）
with app.app_context():
    #db.drop_all()
    db.create_all()

# 設定 Flask-Login 用戶加載
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# 註冊賣家
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        existing_user = User.query.filter_by(username=username).first()
        
        if existing_user:
            flash('賬號已存在，請重新選擇賬號名稱。')
            return redirect(url_for('register'))
        
        # 建立新用戶並加密密碼
        new_user = User(username=username)
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()
        flash('註冊成功，請登入！')
        return redirect(url_for('login'))
    
    return render_template('register.html')

# 登入賣家
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        
        # 檢查密碼是否正確
        if user and user.check_password(password):
            login_user(user)
            flash(f'歡迎，{user.username}！登入成功！')
            return redirect(url_for('index'))
        else:
            flash('登入失敗，請檢查賬號和密碼。')
    
    return render_template('login.html')

# 登出賣家
@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('您已成功登出。')
    return redirect(url_for('login'))

# 首頁，顯示賣家的所有商品
@app.route('/')
@login_required
def index():
    # 只顯示目前登入賣家的商品
    products = Product.query.filter_by(seller_id=current_user.id).all()
    return render_template('index.html', products=products, username=current_user.username)

# 添加商品的頁面
@app.route('/add', methods=['GET', 'POST'])
@login_required
def add_product():
    if request.method == 'POST':
        name = request.form['name']
        price = int(request.form['price'])
        quantity = int(request.form['quantity'])
        
        # 查詢賣家是否已有相同名稱且價格相同的商品
        existing_product = Product.query.filter_by(name=name, price=price, seller_id=current_user.id).first()
        
        if existing_product:
            existing_product.quantity += quantity
        else:
            new_product = Product(name=name, price=price, quantity=quantity, seller_id=current_user.id)
            db.session.add(new_product)
        
        db.session.commit()
        return redirect(url_for('index'))
    
    return render_template('add_product.html')

# 修改商品的頁面
@app.route('/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_product(id):
    product = Product.query.get_or_404(id)
    if product.seller_id != current_user.id:
        flash('您無權限修改此商品')
        return redirect(url_for('index'))

    if request.method == 'POST':
        product.price = int(request.form['price'])
        product.quantity = int(request.form['quantity'])
        db.session.commit()
        return redirect(url_for('index'))
    
    return render_template('edit_product.html', product=product)

# 刪除商品
@app.route('/delete/<int:id>', methods=['POST'])
@login_required
def delete_product(id):
    product = Product.query.get_or_404(id)
    if product.seller_id != current_user.id:
        flash('您無權限刪除此商品')
        return redirect(url_for('index'))
    
    db.session.delete(product)
    db.session.commit()
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)
