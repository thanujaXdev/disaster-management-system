from flask import Flask, render_template, request, redirect, url_for, flash, session
from models import db, User, Disaster, Alert, Shelter, Volunteer
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from functools import wraps
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'disaster-mgmt-secret-2024'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///disaster.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024

db.init_app(app)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please login first.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

def role_required(role):
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if session.get('role') != role:
                flash('Access denied.', 'danger')
                return redirect(url_for('home'))
            return f(*args, **kwargs)
        return decorated
    return decorator

@app.route('/')
def home():
    alerts = Alert.query.order_by(Alert.created_at.desc()).limit(10).all()
    shelters = Shelter.query.all()
    total_disasters = Disaster.query.count()
    total_volunteers = Volunteer.query.count()
    resolved = Disaster.query.filter_by(status='resolved').count()
    return render_template('index.html', alerts=alerts, shelters=shelters,
                           total_disasters=total_disasters,
                           total_volunteers=total_volunteers, resolved=resolved)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            session['role'] = user.role
            session['name'] = user.name
            if user.role == 'admin':
                return redirect(url_for('admin_dashboard'))
            elif user.role == 'volunteer':
                return redirect(url_for('volunteer_dashboard'))
            else:
                return redirect(url_for('citizen_dashboard'))
        flash('Invalid email or password.', 'danger')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        role = request.form['role']
        skills = request.form.get('skills', '')
        if User.query.filter_by(email=email).first():
            flash('Email already registered.', 'danger')
            return redirect(url_for('register'))
        user = User(name=name, email=email,
                    password=generate_password_hash(password), role=role)
        db.session.add(user)
        db.session.flush()
        if role == 'volunteer':
            vol = Volunteer(user_id=user.id, skills=skills)
            db.session.add(vol)
        db.session.commit()
        flash('Registration successful! Please login.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

@app.route('/citizen')
@login_required
def citizen_dashboard():
    my_reports = Disaster.query.filter_by(reported_by=session['user_id']).order_by(Disaster.created_at.desc()).all()
    alerts = Alert.query.order_by(Alert.created_at.desc()).limit(5).all()
    return render_template('citizen_dashboard.html', reports=my_reports, alerts=alerts)

@app.route('/citizen/report', methods=['GET', 'POST'])
@login_required
def report_disaster():
    if request.method == 'POST':
        disaster_type = request.form['disaster_type']
        location = request.form['location']
        description = request.form['description']
        photo_filename = None
        if 'photo' in request.files:
            file = request.files['photo']
            if file and allowed_file(file.filename):
                photo_filename = secure_filename(file.filename)
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], photo_filename))
        disaster = Disaster(disaster_type=disaster_type, location=location,
                            description=description, photo=photo_filename,
                            reported_by=session['user_id'])
        db.session.add(disaster)
        db.session.commit()
        flash('Disaster reported successfully!', 'success')
        return redirect(url_for('citizen_dashboard'))
    return render_template('report_disaster.html')

@app.route('/volunteer')
@login_required
def volunteer_dashboard():
    vol = Volunteer.query.filter_by(user_id=session['user_id']).first()
    alerts = Alert.query.order_by(Alert.created_at.desc()).limit(5).all()
    return render_template('volunteer_dashboard.html', volunteer=vol, alerts=alerts)

@app.route('/shelters')
def shelters():
    all_shelters = Shelter.query.all()
    return render_template('shelters.html', shelters=all_shelters)

@app.route('/admin')
@login_required
@role_required('admin')
def admin_dashboard():
    total_disasters = Disaster.query.count()
    pending = Disaster.query.filter_by(status='reported').count()
    total_volunteers = Volunteer.query.count()
    total_shelters = Shelter.query.count()
    resolved = Disaster.query.filter_by(status='resolved').count()
    recent_reports = Disaster.query.order_by(Disaster.created_at.desc()).limit(5).all()
    disaster_types = db.session.query(Disaster.disaster_type, db.func.count(Disaster.id)).group_by(Disaster.disaster_type).all()
    return render_template('admin_dashboard.html',
                           total_disasters=total_disasters, pending=pending,
                           total_volunteers=total_volunteers,
                           total_shelters=total_shelters, resolved=resolved,
                           recent_reports=recent_reports,
                           disaster_types=disaster_types)

@app.route('/admin/reports')
@login_required
@role_required('admin')
def admin_reports():
    status_filter = request.args.get('status', 'all')
    if status_filter == 'all':
        reports = Disaster.query.order_by(Disaster.created_at.desc()).all()
    else:
        reports = Disaster.query.filter_by(status=status_filter).order_by(Disaster.created_at.desc()).all()
    return render_template('admin_reports.html', reports=reports, status_filter=status_filter)

@app.route('/admin/reports/<int:id>/update', methods=['POST'])
@login_required
@role_required('admin')
def update_report_status(id):
    disaster = Disaster.query.get_or_404(id)
    disaster.status = request.form['status']
    db.session.commit()
    if disaster.status == 'verified':
        alert = Alert(title=f"{disaster.disaster_type} reported in {disaster.location}",
                      message=disaster.description, severity='high')
        db.session.add(alert)
        db.session.commit()
    flash('Status updated successfully.', 'success')
    return redirect(url_for('admin_reports'))

@app.route('/admin/alerts', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def admin_alerts():
    if request.method == 'POST':
        alert = Alert(title=request.form['title'],
                      message=request.form['message'],
                      severity=request.form['severity'])
        db.session.add(alert)
        db.session.commit()
        flash('Alert posted!', 'success')
    alerts = Alert.query.order_by(Alert.created_at.desc()).all()
    return render_template('admin_alerts.html', alerts=alerts)

@app.route('/admin/alerts/<int:id>/delete', methods=['POST'])
@login_required
@role_required('admin')
def delete_alert(id):
    alert = Alert.query.get_or_404(id)
    db.session.delete(alert)
    db.session.commit()
    flash('Alert deleted.', 'success')
    return redirect(url_for('admin_alerts'))

@app.route('/admin/volunteers')
@login_required
@role_required('admin')
def admin_volunteers():
    volunteers = db.session.query(Volunteer, User).join(User, Volunteer.user_id == User.id).all()
    return render_template('admin_volunteers.html', volunteers=volunteers)

@app.route('/admin/volunteers/<int:id>/assign', methods=['POST'])
@login_required
@role_required('admin')
def assign_volunteer(id):
    vol = Volunteer.query.get_or_404(id)
    vol.assigned_task = request.form['task']
    vol.assigned_location = request.form['location']
    vol.status = 'assigned'
    db.session.commit()
    flash('Volunteer assigned successfully!', 'success')
    return redirect(url_for('admin_volunteers'))

@app.route('/admin/shelters', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def admin_shelters():
    if request.method == 'POST':
        shelter = Shelter(
            name=request.form['name'],
            address=request.form['address'],
            lat=float(request.form['lat']),
            lng=float(request.form['lng']),
            total_capacity=int(request.form['total_capacity']),
            available_beds=int(request.form['available_beds']),
            has_medical=bool(request.form.get('has_medical'))
        )
        db.session.add(shelter)
        db.session.commit()
        flash('Shelter added!', 'success')
    shelters = Shelter.query.all()
    return render_template('admin_shelters.html', shelters=shelters)

@app.route('/admin/shelters/<int:id>/delete', methods=['POST'])
@login_required
@role_required('admin')
def delete_shelter(id):
    shelter = Shelter.query.get_or_404(id)
    db.session.delete(shelter)
    db.session.commit()
    flash('Shelter removed.', 'success')
    return redirect(url_for('admin_shelters'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        if not User.query.filter_by(email='admin@disaster.com').first():
            admin = User(name='Admin', email='admin@disaster.com',
                        password=generate_password_hash('admin123'), role='admin')
            db.session.add(admin)
            db.session.commit()
            print("✅ Default admin created: admin@disaster.com / admin123")
    app.run(debug=True)
