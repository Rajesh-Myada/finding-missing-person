from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
import face_recognition
from PIL import Image
from io import BytesIO
import base64
from datetime import datetime
import matplotlib
import matplotlib.pyplot as plt, imageio, numpy as np
from flask_mail import Mail, Message
import csv
import io
import os
matplotlib.use('Agg')


app = Flask(__name__)

app.secret_key = "abc"  

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///missing.db"
db = SQLAlchemy(app)

app.config['MAIL_SERVER']='sandbox.smtp.mailtrap.io'
app.config['MAIL_PORT'] = 2525
app.config['MAIL_USERNAME'] = '0004567fd6c17d'
app.config['MAIL_PASSWORD'] = '588c01184eb5c7'
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USE_SSL'] = False
app.config['TESTING'] = False
mail = Mail(app)
class MissingPerson(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    parent_email = db.Column(db.String(50), nullable=False)
    police_id = db.Column(db.Integer)
    name = db.Column(db.String(30), nullable=False)
    location = db.Column(db.String(50), nullable=False)
    phno = db.Column(db.String(50), nullable=False)
    date = db.Column(db.String(50), nullable=False)
    image = db.Column(db.LargeBinary, nullable=False)
    status = db.Column(db.String(100))

class PersonFound(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    missing_person_id = db.Column(db.String(50),nullable=False)
    location = db.Column(db.String(50), nullable=False)
    image = db.Column(db.LargeBinary, nullable=False)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(30), nullable=False)
    password = db.Column(db.String(30), nullable=False)
    email = db.Column(db.String(50), nullable=False)
    role = db.Column(db.String(20), nullable=False)

class Chat(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    case = db.Column(db.String(10))
    username = db.Column(db.String(80))
    message = db.Column(db.String(200))
    timestamp = db.Column(db.DateTime)

class Police(db.Model):
    id = db.Column(db.Integer)
    email = db.Column(db.String(50),primary_key = True)

class Volunteer(db.Model):
    id = db.Column(db.Integer,primary_key = True)
    email = db.Column(db.String(50))
    designation = db.Column(db.String(50))

class Parent(db.Model):
    id = db.Column(db.Integer,primary_key = True)
    email = db.Column(db.String(50))

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session or 'name' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function



@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        if db.session.query(db.exists().where(User.email==request.form["email"])).scalar() == False:
        # Get the form data
            name = request.form['name']
            email = request.form['email']
            password = request.form['password']
            role = request.form['role']
            # Create a new user object
            if(role == 'police'):
                police = Police.query.filter_by(email = email).first()
                if(police is None):
                    role = 'volunteer'
            if(role =='volunteer'):
                volunteer = Volunteer.query.filter_by(email = email).first()
                if(volunteer is None):
                    role = 'parent'
            if(role == 'parent'):
                parent = Parent.query.filter_by(email = email).first()
                if(parent is None):
                    role = 'people'

            new_user = User(name=name, email=email, password=password, role=role)

            # Add the user to the database
            db.session.add(new_user)
            db.session.commit()

        # Redirect the user to the login page
            flash("Succesfully Registered ")
            return redirect(url_for('login'))
        else:
            flash("Account ALREADY EXIST")
    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # Get the form data
        email = request.form['email']
        password = request.form['password']

        # Find the user with the matching email and password
        user = User.query.filter_by(email=email, password=password).first()
        if user:
            # If a user is found, log them in
            session['user_id'] = user.id
            session['name'] = user.name
            if(user.role!='null'):
                session['role'] = user.role
            if(user.role=='admin'):
                return redirect(url_for('upload_csv'))
            if(user.role=='police'):
                missing_persons = MissingPerson.query.all()
                # Convert each missing person's image to a base64 string
                for missing_person in missing_persons:
                    image_file = BytesIO(missing_person.image)
                    image_data = base64.b64encode(image_file.getvalue()).decode('utf-8')
                    missing_person.image = "data:image/jpeg;base64,{}".format(image_data)
                return render_template('register.html',session=session, missing_persons=missing_persons)
            if(user.role=='volunteer'):
                missing_persons = MissingPerson.query.filter_by(status="Active").all()
            # Convert each missing person's image to a base64 string
                for missing_person in missing_persons:
                    image_file = BytesIO(missing_person.image)
                    image_data = base64.b64encode(image_file.getvalue()).decode('utf-8')
                    missing_person.image = "data:image/jpeg;base64,{}".format(image_data)
                return render_template('volunteer.html',session=session, missing_persons=missing_persons)
            if(user.role=='people'):
                missing_persons = MissingPerson.query.filter_by(status="Active").all()
            # Convert each missing person's image to a base64 string
                for missing_person in missing_persons:
                    image_file = BytesIO(missing_person.image)
                    image_data = base64.b64encode(image_file.getvalue()).decode('utf-8')
                    missing_person.image = "data:image/jpeg;base64,{}".format(image_data)
                return render_template('common_ppl.html',session=session, missing_persons=missing_persons)
            if(user.role=='parent'):
                user = User.query.filter_by(id= session['user_id']).first()
                mcase = MissingPerson.query.filter_by(parent_email = user.email).all()
                for case in mcase:
                    case.police_id = User.query.filter_by(id = case.police_id).first().name
                lens=MissingPerson.query.filter_by(parent_email = user.email).count()
                return render_template("parent.html",all_detail = mcase,len=lens)
            if(user.role=='null'):
                flash('You are not verified by admin please wait for a day!')
                return redirect(url_for('login'))
        else:
            # If no user is found, redirect to the login page with an error message
            flash('Invalid email or password')
            return redirect(url_for('login'))

    return render_template('login.html', message=request.args.get('message'))


@app.route('/upload_csv', methods=['POST','GET'])
def upload_csv():
    if request.method == 'POST':
        csv_file = request.files['csv_file']
        if not csv_file:
            flash('No file uploaded.')
            return render_template('upload_csv.html')
        filename = csv_file.filename
        stream = io.StringIO(csv_file.stream.read().decode("UTF8"), newline=None)
        csv_input = csv.reader(stream)
        next(csv_input) # Skip header row
        for row in csv_input:
            if(filename == 'police.csv'):
                police = Police(id=row[0], email=row[1])
                db.session.add(police)
            else:
                volunteer = Volunteer(email=row[0], designation=row[1])
                db.session.add(volunteer)
        db.session.commit()
        flash('CSV file uploaded successfully.')    
    return render_template('upload_csv.html')



@app.route('/logout')
def logout():
    # Clear the session variables and redirect the user to the login page
    session.clear()
    return redirect(url_for('login'))


@app.route('/acc',methods=['POST'])
def acc():
    uid = request.form["userid"]
    urole = request.form["role"]
    if urole=="remove":
        User.query.filter_by(id=uid).delete()
        db.session.commit()
        return redirect("/admin")

    ad = User.query.filter_by(id = uid).first()
    ad.role = urole
    db.session.commit()
    return redirect("/admin")

@app.route('/admin')
def admin():
    all_details = User.query.filter(User.role=='null')
    lens=User.query.filter(User.role=='null').count()
    return render_template("admin.html",all_detail=all_details,len=lens)


@app.route('/register', methods=['GET', 'POST'])
@login_required
def register():
    if request.method == 'POST':
        name = request.form['name']
        location = request.form['location']
        phno = request.form['phone']
        image = request.files['image']
        date = request.form['date']
        status = request.form['status']
        parent_email = request.form['pemail']
        # Convert the image to a binary object
        image_binary = image.read()
        parent = Parent(email = parent_email)
        db.session.add(parent)
        db.session.commit()
        
        missing_person = MissingPerson(name=name,parent_email= parent_email ,police_id=session['user_id'],phno=phno,status=status,date=date,location=location, image=image_binary)

        db.session.add(missing_person)
        db.session.commit()

        return redirect(url_for('register'))
    status = request.args.get('status')
    if(not status):
        missing_persons = MissingPerson.query.all()
    elif(status):
        missing_persons = MissingPerson.query.filter_by(status=status).all()
        
    # Convert each missing person's image to a base64 string
    for missing_person in missing_persons:
        image_file = BytesIO(missing_person.image)
        image_data = base64.b64encode(image_file.getvalue()).decode('utf-8')
        missing_person.image = "data:image/jpeg;base64,{}".format(image_data)
    return render_template('register.html', missing_persons=missing_persons)


@app.route('/search/<case>', methods=['GET', 'POST'])
@login_required
def search(case):
    if request.method == 'POST':
        location = request.form['location']
        temp=request.files['image']
        image = request.files['image']
        image_binary = temp.read()

        # Load the uploaded image and encode it
        uploaded_image = face_recognition.load_image_file(image)
        no_of_faces = len(face_recognition.face_encodings(uploaded_image))
        if(no_of_faces==0):
            return redirect(url_for('not_found'))
        uploaded_image_encodings = face_recognition.face_encodings(uploaded_image)

        # Find all missing persons in the given location
        missing_person = MissingPerson.query.filter_by(id=case).first()

        # Iterate over the missing persons and check if the uploaded image matches any of them
        
            # Load the missing person's image and encode it
        missing_person_image = face_recognition.load_image_file(BytesIO(missing_person.image))
        missing_person_image_encoding = face_recognition.face_encodings(missing_person_image)[0]
        # Check if the uploaded image matches the missing person's image
        flag=0
        for uploaded_image_encoding in uploaded_image_encodings:
            result = face_recognition.compare_faces([uploaded_image_encoding], missing_person_image_encoding,tolerance=0.6)
            if result[0]:
                user = User.query.filter_by(id=session['user_id']).first()
                polices = User.query.filter_by(role='police').all()
                police_list = []
                for police in polices:
                    police_list.append(police.email)
                flag=1
                #send mail
                msg = Message('EMERGANCY: Missing person(case no.'+case+") FOUND by "+session["name"], sender = user.email, recipients = police_list)
                msg.body = 'Missing person has been found by '+session["name"] +" who is a "+ session['role'] + 'at location ' + location
                mail.send(msg)
                #changing status
                person_found = PersonFound(missing_person_id=missing_person.id,location=location, image=image_binary)
                db.session.add(person_found)
                db.session.commit()
                updateStatus=MissingPerson.query.filter_by(id=case).first()
                updateStatus.status='Confirmation_Required'
                db.session.commit()

                # If the uploaded image matches the missing person's image, redirect to the success page
                return redirect(url_for('success',mid=missing_person.id,fid=person_found.id))   
            
            # If no missing persons were found, redirect to the not_found page
        if flag==0:
            print(request.path)
            return render_template('not_found.html',url=request.path)
    return render_template('search.html')

@app.route('/missing_persons')
@login_required
def missing_persons():
    # Get all missing persons from the database
    missing_persons = MissingPerson.query.all()

    # Convert each missing person's image to a base64 string
    for missing_person in missing_persons:
        image_file = BytesIO(missing_person.image)
        image_data = base64.b64encode(image_file.getvalue()).decode('utf-8')
        missing_person.image = "data:image/jpeg;base64,{}".format(image_data)

    return render_template('missing_persons.html', missing_persons=missing_persons)

@app.route('/registration_success')
def registration_success():
    return render_template('registration_success.html')


@app.route('/checkagain/<case>',  methods=['GET', 'POST'])
def checkagain(case):
    person_found1 = PersonFound.query.filter_by(missing_person_id=case).first()
    missing_person = MissingPerson.query.filter_by(id=case).first()
    user = User.query.filter_by(id = session['user_id']).first()
    if request.method == 'POST':
        msg = Message('EMERGANCY: Missing person(case no.'+case+") FOUND", sender = user.email, recipients = [missing_person.parent_email])
        msg.body = 'Missing person has been found at '+ person_found1.location 
        mail.send(msg)
        missing_persons = MissingPerson.query.all()
        for missing_person in missing_persons:
            image_file = BytesIO(missing_person.image)
            image_data = base64.b64encode(image_file.getvalue()).decode('utf-8')
            missing_person.image = "data:image/jpeg;base64,{}".format(image_data)
        return render_template('register.html',session=session, missing_persons=missing_persons, mailsent=True)
    else:
        person_found = PersonFound.query.filter_by(id=person_found1.id).first()
        image1 = missing_person.image
        image2 = person_found.image

        # Convert the image from a binary object to an image file
        image_file1 = BytesIO(image1)
        image1 = Image.open(image_file1)

        # Encode the image as a base64 string
        image_data1 = base64.b64encode(image_file1.getvalue()).decode('utf-8')
        image_data1 = "data:image/jpeg;base64,{}".format(image_data1)
        # Convert the image from a binary object to an image file
        image_file2 = BytesIO(image2)
        image2 = Image.open(image_file2)

        # Encode the image as a base64 string
        image_data2 = base64.b64encode(image_file2.getvalue()).decode('utf-8')
        image_data2 = "data:image/jpeg;base64,{}".format(image_data2)

        return render_template('checkagain.html', image1=image_data1,image2=image_data2,case=case)

@app.route('/success')
def success():
    mid=request.args.get("mid")
    fid=request.args.get("fid")
    missing_person = MissingPerson.query.filter_by(id=mid).first()
    person_found = PersonFound.query.filter_by(id=fid).first()
    image1 = missing_person.image
    image2 = person_found.image

    # Convert the image from a binary object to an image file
    image_file1 = BytesIO(image1)
    image1 = Image.open(image_file1)

    # Encode the image as a base64 string
    image_data1 = base64.b64encode(image_file1.getvalue()).decode('utf-8')
    image_data1 = "data:image/jpeg;base64,{}".format(image_data1)
    # Convert the image from a binary object to an image file
    image_file2 = BytesIO(image2)
    image2 = Image.open(image_file2)

    # Encode the image as a base64 string
    image_data2 = base64.b64encode(image_file2.getvalue()).decode('utf-8')
    image_data2 = "data:image/jpeg;base64,{}".format(image_data2)

    return render_template('success.html', image1=image_data1,image2=image_data2)



@app.route('/chat/<case>', methods=['GET','POST'])
@login_required
def chat(case):
    if request.method == 'POST':
        username = session['name']
        message = request.form['message']
        timestamp = datetime.utcnow()

        db.session.add(Chat(case=case,username=username, message=message, timestamp=timestamp))
        db.session.commit()

        return redirect(url_for('chat', case=case))
    messages = Chat.query.filter_by(case=case).order_by(Chat.timestamp.asc()).limit(100).all()
    return render_template('chat.html', messages=messages,session=session)


@app.route('/update/<case>',methods=['POST'])
@login_required
def update(case):
    status = request.form['status']
    updateStatus=MissingPerson.query.filter_by(id=case).first()
    updateStatus.status=status
    db.session.commit()
    missing_persons = MissingPerson.query.all()
    for missing_person in missing_persons:
        image_file = BytesIO(missing_person.image)
        image_data = base64.b64encode(image_file.getvalue()).decode('utf-8')
        missing_person.image = "data:image/jpeg;base64,{}".format(image_data)
    return render_template('register.html',session=session, missing_persons=missing_persons)


@app.route('/withdraw/<case>',methods=['POST'])
@login_required
def withdraw(case):
    MissingPerson.query.filter_by(id=case).delete() 
    db.session.commit()
    missing_persons = MissingPerson.query.all()
            # Convert each missing person's image to a base64 string
    for missing_person in missing_persons:
        image_file = BytesIO(missing_person.image)
        image_data = base64.b64encode(image_file.getvalue()).decode('utf-8')
        missing_person.image = "data:image/jpeg;base64,{}".format(image_data)
    return render_template('register.html',session=session, missing_persons=missing_persons)


@app.route('/withdrawcase/<case>',methods=['POST'])
@login_required
def mycase(case):
    MissingPerson.query.filter_by(id=case).delete()
    db.session.commit()
    user = User.query.filter_by(id= session['user_id']).first()
    mcase = MissingPerson.query.filter_by(parent_email = user.email).all()
    lens=MissingPerson.query.filter_by(parent_email = user.email).count()
    return render_template("parent.html",all_detail = mcase,len=lens)

@app.route('/not_found')
def not_found():
    return render_template('not_found.html')


@app.route('/generate_poster', methods=['POST','GET'])
@login_required
def poster():
    if request.method == 'POST':
        name = request.form['name']
        contact = request.form['contact']
        contact_nmbr = request.form['contact_number']
        age = request.form['age']
        height = request.form['height']
        weight = request.form['weight']
        last_seen_location = request.form['last_seen_location']
        profile_pic = request.files['profile_pic']

        # save uploaded image
        profile_pic.save(profile_pic.filename)

        # define poster dimensions
        size = (4.62, 6.93)
        margin = 0
        dpi = 100

        # load the background image
        image = imageio.imread('static/missing.jpg')

        # create the plot
        plt.figure('poster', figsize=size, dpi=dpi)
        a = plt.subplot()
        a.cla()
        plt.setp(a.get_xticklabels(), visible=False)
        plt.setp(a.get_xticklines(), visible=False)
        plt.setp(a.get_yticklabels(), visible=False)
        plt.setp(a.get_yticklines(), visible=False)
        plt.subplots_adjust(left=margin/size[0], right=1.0 - margin/size[0], top=1.0 - margin/size[1], bottom=margin/size[1])

        # draw the background image
        a.imshow(image, interpolation='nearest', extent=[0, size[0], 0, size[1]])

        # add text to the poster
        a.text(2.31, 1.4, 'Name: ' + name.upper(), fontsize=20, ha='center', weight='bold', color='red')
        a.text(2.31, 0.5, 'Please contact ' + contact.upper() + ' if found', fontsize=12, ha='center', weight='bold', color='orangered')
        a.text(2.31, 0.35, 'Phone Number: ' + contact_nmbr.upper(), fontsize=12, color='orangered', ha='center', weight='bold', va='top')
        a.text(2.31, 0.95, 'Last Seen Location: ' + last_seen_location, fontsize=10, color='black', ha='center', weight='bold')
        a.text(2.31, 1.15, 'Age = '+ age + ' | Height = ' + height + ' | Weight = ' + weight, fontsize=10, color='black', ha='center', weight='bold')

        # save the poster as a PNG file
        filename = name.replace(' ', '').replace('\n','') + '.png'
        plt.savefig(filename)
        plt.draw()

        # add profile picture to poster
        img = Image.open(profile_pic).convert("RGBA")
        img = img.resize((320, 331), Image.ANTIALIAS)
        background = Image.open(filename).convert("RGBA")
        background.paste(img, (71, 166), img)
        background.save('./Static/'+filename,"PNG")

        for file in os.listdir('.'):
            if file != filename and (file.endswith('.png') or file.endswith('.jpg') ):
                os.remove(file)

        return render_template('poster.html', name=name, filename=filename)
    else:
        return render_template('poster.html')









if __name__ == '__main__':
  app.run(debug=True)

