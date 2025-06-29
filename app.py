from flask import Flask, render_template, redirect, url_for, flash, request, abort
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, current_user, logout_user, login_required
from flask_bcrypt import Bcrypt
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, SelectField, BooleanField, IntegerField, TextAreaField, DateTimeLocalField
from wtforms.validators import DataRequired, Length, Email, EqualTo, NumberRange
from datetime import datetime, timedelta
import os
from flask_migrate import Migrate
from werkzeug.utils import secure_filename
from flask import Blueprint
from sqlalchemy.orm import Session


app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///university_kindergarten.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

children_bp = Blueprint('children', __name__)

def get_booking(booking_id):
    booking = db.session.get(Booking, booking_id)
    return booking

UPLOAD_FOLDER = 'static/images/children'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

db = SQLAlchemy(app)
migrate = Migrate(app, db)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message_category = 'info'


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(60), nullable=False)
    role = db.Column(db.String(20), nullable=False)
    registration_number = db.Column(db.String(50), unique=True, nullable=False)
    children = db.relationship('Child', backref='parent', lazy=True)

class Child(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    age = db.Column(db.Integer, nullable=False)
    image = db.Column(db.String(20), nullable=False, default='default.jpg')
    health_status = db.Column(db.Text, nullable=True)
    parent_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    date_created = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    bookings = db.relationship('Booking', backref='child', lazy=True)
    attendances = db.relationship('Attendance', backref='child', lazy=True)

class Booking(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    child_id = db.Column(db.Integer, db.ForeignKey('child.id'), nullable=False)
    booking_type = db.Column(db.String(20), nullable=False)
    start_date = db.Column(db.DateTime, nullable=False)
    end_date = db.Column(db.DateTime, nullable=False)
    amount = db.Column(db.Float, nullable=False)
    is_paid = db.Column(db.Boolean, default=False)
    payment_date = db.Column(db.DateTime, nullable=True)

class Attendance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    child_id = db.Column(db.Integer, db.ForeignKey('child.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(20), nullable=False)

class Activity(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    image = db.Column(db.String(20), nullable=False)
    date = db.Column(db.Date, nullable=False)

class WeeklySchedule(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    day = db.Column(db.String(15), nullable=False)
    activity = db.Column(db.String(100), nullable=False)
    time = db.Column(db.String(50), nullable=False)

with app.app_context():
    try:
        from sqlalchemy import text
        db.session.execute(text('ALTER TABLE child ADD COLUMN date_created DATETIME'))
        db.session.execute(text('UPDATE child SET date_created = :date'), {'date': datetime.utcnow()})
        db.session.commit()
    except Exception as e:
        print("Column already exists or other error:", e)
        db.session.rollback()

class RegistrationForm(FlaskForm):
    username = StringField('اسم المستخدم', validators=[DataRequired(), Length(min=2, max=20)])
    email = StringField('البريد الإلكتروني', validators=[DataRequired(), Email()])
    password = PasswordField('كلمة المرور', validators=[DataRequired()])
    confirm_password = PasswordField('تأكيد كلمة المرور', validators=[DataRequired(), EqualTo('password')])
    role = SelectField('الدور', choices=[
        ('طالب', 'طالب'),
        ('موظف', 'موظف'),
        ('عامل', 'عامل'),
        ('أستاذ جامعي', 'أستاذ جامعي')
    ], validators=[DataRequired()])
    registration_number = StringField('رقم التسجيل/الوظيفي', validators=[DataRequired()])
    submit = SubmitField('تسجيل')

class LoginForm(FlaskForm):
    registration_number = StringField('رقم التسجيل/الوظيفي', validators=[DataRequired()])
    password = PasswordField('كلمة المرور', validators=[DataRequired()])
    remember = BooleanField('تذكرني')
    submit = SubmitField('تسجيل الدخول')

class ChildForm(FlaskForm):
    name = StringField('اسم الطفل', validators=[DataRequired()])
    age = IntegerField('العمر', validators=[DataRequired(), NumberRange(min=1, max=6)])
    health_status = TextAreaField('الوضع الصحي')
    submit = SubmitField('حفظ')

class BookingForm(FlaskForm):
    child_id = SelectField('الطفل', coerce=int, validators=[DataRequired()])
    booking_type = SelectField('نوع الحجز', choices=[
        ('بالساعة', 'بالساعة'),
        ('جزئي', 'جزئي (نصف يوم)'),
        ('كلي', 'كلي (يوم كامل)')
    ], validators=[DataRequired()])
    start_date = DateTimeLocalField('تاريخ البدء', format='%Y-%m-%dT%H:%M', validators=[DataRequired()])
    end_date = DateTimeLocalField('تاريخ الانتهاء', format='%Y-%m-%dT%H:%M', validators=[DataRequired()])
    submit = SubmitField('حجز')

# Routes
@app.route('/')
@app.route('/home')
def home():
    activities = Activity.query.order_by(Activity.date.desc()).limit(4).all()
    return render_template('main/home.html', activities=activities)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    
    form = RegistrationForm()
    
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        user = User(
            username=form.username.data,
            email=form.email.data,
            password=hashed_password,
            role=form.role.data,
            registration_number=form.registration_number.data
        )
        db.session.add(user)
        db.session.commit()
        flash('تم إنشاء حسابك بنجاح! يمكنك الآن تسجيل الدخول', 'success')
        return redirect(url_for('login'))
    
    return render_template('auth/register.html', title='تسجيل جديد', form=form)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    form = LoginForm()
    
    if form.validate_on_submit():
        user = User.query.filter_by(registration_number=form.registration_number.data).first()
        if user and bcrypt.check_password_hash(user.password, form.password.data):
            login_user(user, remember=form.remember.data)
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('dashboard'))
        else:
            flash('تسجيل الدخول غير ناجح. الرجاء التحقق من الرقم الوظيفي وكلمة المرور', 'danger')
    
    return render_template('auth/login.html', title='تسجيل الدخول', form=form)

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('home'))

@app.route('/dashboard')
@login_required
def dashboard():
    children = current_user.children
    weekly_schedule = WeeklySchedule.query.order_by(WeeklySchedule.id).all()
    
    schedule_by_day = {}
    for item in weekly_schedule:
        if item.day not in schedule_by_day:
            schedule_by_day[item.day] = []
        schedule_by_day[item.day].append(item)
    
    return render_template('main/dashboard.html', 
                         title='لوحة التحكم',
                         children=children,
                         schedule=schedule_by_day)

@app.route('/children', methods=['GET', 'POST'])
@login_required
def manage_children():
    form = ChildForm()
    
    if form.validate_on_submit():
        image_file = 'default.jpg'
        if 'image' in request.files:
            file = request.files['image']
            if file.filename != '' and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                image_file = filename
        
        child = Child(
            name=form.name.data,
            age=form.age.data,
            health_status=form.health_status.data,
            parent_id=current_user.id,
            image=image_file
        )
        db.session.add(child)
        db.session.commit()
        flash('تمت إضافة الطفل بنجاح', 'success')
        return redirect(url_for('manage_children'))
    
    children = Child.query.filter_by(parent_id=current_user.id).all()
    return render_template('children/manage_children.html', 
                         title='إدارة الأطفال', 
                         form=form, 
                         children=children)

@children_bp.route('/child/<int:child_id>')
@login_required
def child_profile(child_id):
    child = Child.query.get_or_404(child_id)
    if child.parent_id != current_user.id:
        flash('ليس لديك صلاحية الوصول إلى هذا الملف', 'danger')
        return redirect(url_for('home'))
    return render_template('children/child_profile.html', 
                         title='ملف الطفل', 
                         child=child)  

@app.route('/child/<int:child_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_child(child_id):
    child = Child.query.get_or_404(child_id)
    if child.parent_id != current_user.id:
        flash('ليس لديك صلاحية لتعديل هذا الملف', 'danger')
        return redirect(url_for('home'))
    
    form = ChildForm(obj=child)
    
    if form.validate_on_submit():
        form.populate_obj(child)
        db.session.commit()
        flash('تم تحديث ملف الطفل بنجاح', 'success')
        return redirect(url_for('child_profile', child_id=child.id))
    
    return render_template('children/edit_child.html', 
                         title='تعديل ملف الطفل', 
                         form=form, 
                         child=child)

@app.route('/book', methods=['GET', 'POST'])
@login_required
def book():
    form = BookingForm()
    form.child_id.choices = [(child.id, child.name) for child in current_user.children]
    
    if form.validate_on_submit():
        if form.booking_type.data == 'بالساعة':
            hours = (form.end_date.data - form.start_date.data).total_seconds() / 3600
            amount = hours * 50
        elif form.booking_type.data == 'جزئي':
            amount = 500
        else:
            amount = 1000
        
        booking = Booking(
            child_id=form.child_id.data,
            booking_type=form.booking_type.data,
            start_date=form.start_date.data,
            end_date=form.end_date.data,
            amount=amount,
            is_paid=False
        )
        db.session.add(booking)
        db.session.commit()
        flash('تم الحجز بنجاح. الرجاء إتمام الدفع', 'success')
        return redirect(url_for('payment', booking_id=booking.id))
    
    return render_template('payments/book.html', title='حجز جديد', form=form)

@app.route('/payment/<int:booking_id>', methods=['GET', 'POST'])
@login_required
def payment(booking_id):
    booking = Booking.query.get_or_404(booking_id)
    child = Child.query.get_or_404(booking.child_id)
    
    if child.parent_id != current_user.id:
        flash('ليس لديك صلاحية الوصول إلى هذه الصفحة', 'danger')
        return redirect(url_for('home'))
    
    if request.method == 'POST':
        booking.is_paid = True
        booking.payment_date = datetime.utcnow()
        db.session.commit()
        flash('تم الدفع بنجاح', 'success')
        return redirect(url_for('payment_success', booking_id=booking.id))
    
    return render_template('payments/payment.html', title='الدفع', booking=booking)

@app.route('/payment_success/<int:booking_id>', methods=['GET', 'POST'])
@login_required
def payment_success(booking_id):
    booking = Booking.query.get_or_404(booking_id)
    child = Child.query.get_or_404(booking.child_id)
    
    if child.parent_id != current_user.id:
        flash('ليس لديك صلاحية الوصول إلى هذه الصفحة', 'danger')
        return redirect(url_for('home'))
    
    if request.method == 'POST':
        booking.is_paid = True
        booking.payment_date = datetime.utcnow()
        db.session.commit()
    
    return render_template('payments/payment_success.html', 
                         title='تم الدفع بنجاح', 
                         booking=booking)

payments_bp = Blueprint('payments', __name__, template_folder='templates')
app.register_blueprint(children_bp, url_prefix='/children')
app.register_blueprint(payments_bp, url_prefix='/payments')

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(host='0.0.0.0', debug=True) 