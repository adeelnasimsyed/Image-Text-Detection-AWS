'''

main file, holds all methods

'''

from flask import session, request, render_template, redirect, url_for, flash, logging, send_from_directory
from flask_mysqldb import MySQL
from wtforms import Form, StringField, PasswordField, TextAreaField, validators
from app import webapp
import os
from passlib.hash import sha256_crypt
from functools import wraps
from werkzeug.utils import secure_filename
from datetime import datetime
import subprocess


webapp.secret_key = '\x80\xa9s*\x12\xc7x\xa9d\x1f(\x03\xbeHJ:\x9f\xf0!\xb1a\xaa\x0f\xee'

#Config MySQL
webapp.config['MYSQL_HOST'] = 'localhost'
webapp.config['MYSQL_USER'] = 'root'
webapp.config['MYSQL_PASSWORD'] = 'password'
webapp.config['MYSQL_DB'] = 'ece1779_a1'
webapp.config['MYSQL_CURSORCLASS'] = 'DictCursor'

#init MySQL
mysql = MySQL(webapp)

#landing page
@webapp.route('/')
def main():

	return render_template("home.html")


#About page, gives info about application and development team
@webapp.route('/about')
def about():
	
	return render_template("about.html")

#class for Register form, used to register new users also does validation of form
class RegisterForm(Form):
	name = StringField('Name', [validators.Length(min = 1, max = 50)])
	username = StringField('Username', [validators.Length(min = 4, max = 25)])
	email = StringField('Email', [validators.Length(min = 6, max = 50)])
	password = PasswordField('Password', [
		validators.DataRequired(),
		validators.EqualTo('confirm', message = 'Passwords do not match')
		])
	confirm = PasswordField('Confirm Password')

@webapp.route('/register', methods = ['GET', 'POST'])
def register():
	form = RegisterForm(request.form)
	if request.method == 'POST' and form.validate():
		name  = form.name.data 
		email = form.email.data 
		username = form.username.data 
		password = sha256_crypt.encrypt(str(form.password.data))

		#Create cursor
		cur = mysql.connection.cursor()

		cur.execute("INSERT INTO users(name, email, username, password) VALUES(%s, %s, %s, %s)",(name, email, username, password))

		#Commit to DB
		mysql.connection.commit()

		#Close connection
		cur.close()

		flash('Thank you for registering. You can now log in.', 'success')
		return redirect(url_for('login'))
		
	return render_template("register.html", form = form)

#User login
@webapp.route('/login', methods = ['GET', 'POST'])
def login():
	
	if request.method == 'POST':
		#Get Form Fields
		username = request.form['username']
		password_check = request.form['password']

		#Create cursor
		cur = mysql.connection.cursor()

		#Get username from database
		result = cur.execute("SELECT * FROM users WHERE username = %s", [username])

		if result > 0:
			#Get stored password which is hashed
			data = cur.fetchone()
			password = data['password']

			#Compare passwords
			if sha256_crypt.verify(password_check, password):
				#Passed
				session['logged_in'] = True
				session['username'] = username


				flash('You are now logged in', 'success')
				return redirect(url_for('dashboard'))

			else:
				error = 'Invalid login'
				return render_template('login.html', error = error)
			#close connection
			cur.close()	
		else:
			error = 'Username not found'
			return render_template('login.html', error = error)
			 
	return render_template('login.html')

#Do not allow log out when not logged in
def is_logged_in(f):
	@wraps(f)
	def wrap(*args, **kwargs):
		if 'logged_in' in session:
			return f(*args, **kwargs)
		else:
			flash('Please log in', 'danger')
			return redirect(url_for('login'))
	return wrap

webapp.config["IMAGE_UPLOADS"] = "C:/Users/adeel/Desktop/UofT/ECE1779/Assignment_1/app/static/img_uploads"
webapp.config["ALLOWED_IMAGE_EXT"] = ["PNG", "JPG", "JPEG"]

#User dashboard
@webapp.route('/dashboard', methods = ['GET', 'POST'])
@is_logged_in
def dashboard():

	#Create cursor
	cur = mysql.connection.cursor()

	#Execute
	result = cur.execute("SELECT * FROM photos WHERE username LIKE %s", [session['username']])

	photos = cur.fetchall()
	
	if result > 0:
		return render_template("dashboard.html", photos = photos)
						
	#Close connection
	cur.close()

	return render_template("dashboard.html")



def allowed_img(filename):

	if not "." in filename:
		return False

	ext = filename.rsplit(".", 1)[1]

	if ext.upper() in webapp.config["ALLOWED_IMAGE_EXT"]:
		return True
	else:
		return False

#User add photo
@webapp.route('/add_photo', methods = ['GET', 'POST'])
@is_logged_in
def add_photo():

	if request.method == 'POST':

		if request.files:

			image = request.files["image"]

			if image.filename == "":

				flash('Image must have a filename', 'danger')
				return redirect(url_for('add_photo'))

			if not allowed_img(image.filename):

				flash('Image is not a valid extension', 'danger')
				return redirect(url_for('add_photo'))

			else:

				now = datetime.now()
				now_str = now.strftime("%d_%m_%Y__%H_%M_%S")
				filename = secure_filename(image.filename)

				
				filename = str(session['username'])+"_"+now_str+"_"+filename

				f_edit,ext = filename.split('.')
				filename_edit = f_edit + "_edit." + ext

				file_path = os.path.join(webapp.config["IMAGE_UPLOADS"], filename)
				file_path_edit = os.path.join(webapp.config["IMAGE_UPLOADS"], filename_edit)
				image.save(file_path)
				
				text_edit = "python text_detection.py --image %s --east frozen_east_text_detection.pb" %file_path
				os.system(text_edit)
				
				#Create cursor
				cur = mysql.connection.cursor()

				#Execute
				cur.execute("INSERT INTO photos(username, filename_orginal, filename_edit) VALUES(%s, %s, %s)", (session['username'], filename, filename_edit))
				
				#Commit
				mysql.connection.commit()
				
				#Close connection
				cur.close()
			flash('Photo uploaded successfully', 'success')
			return redirect(url_for('add_photo'))

		
	return render_template("add_photo.html")


#View photo
@webapp.route('/view/<string:saved_name>', methods = ['GET', 'POST'])
@is_logged_in
def view_photo(saved_name):

	#Create cursor
	cur = mysql.connection.cursor()

	#Execute
	result = cur.execute("SELECT * FROM photos WHERE filename_orginal LIKE %s", [saved_name])
				
		
	photo = cur.fetchone()

	if result > 0:
		return render_template("view.html", photo = photo)
						
	#Close connection
	cur.close()

	return redirect(url_for('dashboard'))

#Delete photo
@webapp.route('/delete/<string:saved_name>', methods = ['GET', 'POST'])
@is_logged_in
def delete_photo(saved_name):

	'''
	Functionality to remove from local storage commented out because of issues
	'''
	# Delete original and edited photo from local storage
	# saved_name_edit, ext = saved_name.split('.') 
	# saved_name_edit = saved_name + "_edit." + ext 

	# file_path = os.path.join(webapp.config["IMAGE_UPLOADS"], saved_name)
	# file_path_edit = os.path.join(webapp.config["IMAGE_UPLOADS"], saved_name_edit)
	
	# os.remove(file_path)
	# os.remove(file_path_edit)

	#Remove from database

	#Create cursor
	cur = mysql.connection.cursor()

	#Execute
	result = cur.execute("DELETE FROM photos WHERE filename_orginal LIKE %s", [saved_name])
	
	#Commit
	mysql.connection.commit()
				
	#Close connection
	cur.close()
	
	flash('Photo deleted successfully', 'success')	

	return redirect(url_for('dashboard'))		

	

@webapp.route('/send-image/<filename>')
def send_image(filename):
    return send_from_directory(webapp.config["IMAGE_UPLOADS"], filename = filename)



#User logout
@webapp.route('/logout',methods=['GET','POST'])
@is_logged_in
def logout():
	session.clear()
	flash('You are now logged out', 'success')
	return redirect(url_for('login'))



#API to register new user
@webapp.route('/api/register', methods = ['GET', 'POST'])
def api_register():
	if request.method == 'POST':
		
		username = request.form['username']
		password = sha256_crypt.encrypt(str(request.form['password']))

		#Create cursor
		cur = mysql.connection.cursor()

		cur.execute("INSERT INTO users(username, password) VALUES(%s, %s)",(username, password))

		#Commit to DB
		mysql.connection.commit()

		#Close connection
		cur.close()

		return redirect(url_for('api_upload'))
		
	return render_template("api_register.html")


#API for upload, this is a bare bones application just to allow user to upload photos
#We do not check username/password
@webapp.route('/api/upload', methods = ['GET', 'POST'])
def api_upload():
	if request.method == 'POST':

		if request.files:

			username = request.form['username']
			password = sha256_crypt.encrypt(str(request.form['password']))
			image = request.files['file']

			now = datetime.now()
			now_str = now.strftime("%d_%m_%Y__%H_%M_%S")
			filename = secure_filename(image.filename)

				
			filename = str(session['username'])+"_"+now_str+"_"+filename

			f_edit,ext = filename.split('.')
			filename_edit = f_edit + "_edit." + ext

			file_path = os.path.join(webapp.config["IMAGE_UPLOADS"], filename)
			file_path_edit = os.path.join(webapp.config["IMAGE_UPLOADS"], filename_edit)
			image.save(file_path)
				
			text_edit = "python text_detection.py --image %s --east frozen_east_text_detection.pb" %file_path
			os.system(text_edit)
				
			#Create cursor
			cur = mysql.connection.cursor()

			#Execute
			cur.execute("INSERT INTO photos(username, filename_orginal, filename_edit) VALUES(%s, %s, %s)", (username, filename, filename_edit))

			#Commit
			mysql.connection.commit()

			#Close connection
			cur.close()

			return redirect(url_for('api_upload'))

		
	return render_template("api_upload.html")