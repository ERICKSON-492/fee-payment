from flask import Flask, render_template, request, redirect, url_for, flash
import sqlite3
import os
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'your-secret-key'  # For flash messages

DB_PATH = 'database.db'

def init_db():
    if not os.path.exists(DB_PATH):
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        # Students table
        c.execute('''
            CREATE TABLE students (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                admission_no TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                form TEXT NOT NULL
            )
        ''')
        # Terms table
        c.execute('''
            CREATE TABLE terms (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                amount REAL NOT NULL
            )
        ''')
        # Payments table
        c.execute('''
            CREATE TABLE payments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id INTEGER NOT NULL,
                term_id INTEGER NOT NULL,
                amount_paid REAL NOT NULL,
                payment_date TEXT NOT NULL,
                FOREIGN KEY(student_id) REFERENCES students(id),
                FOREIGN KEY(term_id) REFERENCES terms(id)
            )
        ''')
        conn.commit()
        conn.close()

def query_db(query, args=(), one=False):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.execute(query, args)
    rv = cur.fetchall()
    conn.commit()
    conn.close()
    return (rv[0] if rv else None) if one else rv

@app.route('/')
def home():
    return redirect(url_for('view_students'))

@app.route('/students')
def view_students():
    students = query_db('SELECT * FROM students')
    return render_template('students.html', students=students)

@app.route('/terms')
def view_terms():
    terms = query_db('SELECT * FROM terms')
    return render_template('terms.html', terms=terms)

@app.route('/payments')
def view_payments():
    payments = query_db('''
        SELECT payments.id, students.name AS student_name, students.admission_no,
               terms.name AS term_name, payments.amount_paid, payments.payment_date
        FROM payments
        JOIN students ON payments.student_id = students.id
        JOIN terms ON payments.term_id = terms.id
        ORDER BY payments.payment_date DESC
    ''')
    students = query_db('SELECT * FROM students')
    terms = query_db('SELECT * FROM terms')
    return render_template('payments.html', payments=payments, students=students, terms=terms)

@app.route('/student/add', methods=['POST'])
def add_student():
    admission_no = request.form['admission_no']
    name = request.form['name']
    form = request.form['form']
    try:
        query_db('INSERT INTO students (admission_no, name, form) VALUES (?, ?, ?)', 
                 (admission_no, name, form))
        flash("Student added successfully.")
    except sqlite3.IntegrityError:
        flash("Admission number must be unique.")
    return redirect(url_for('view_students'))

@app.route('/term/add', methods=['POST'])
def add_term():
    name = request.form['term_name']
    amount = request.form['amount']
    try:
        query_db('INSERT INTO terms (name, amount) VALUES (?, ?)', (name, amount))
        flash("Term added successfully.")
    except sqlite3.IntegrityError:
        flash("Term name must be unique.")
    return redirect(url_for('view_terms'))

@app.route('/add_payment', methods=['POST'])
def add_payment():
    student_input = request.form.get('student_input', '').strip()
    if not student_input:
        flash("Student input is required.")
        return redirect(url_for('view_payments'))

    try:
        student_id_str = student_input.split(' - ')[0]
        student_id = int(student_id_str)
    except (IndexError, ValueError):
        flash("Invalid student input format. Use 'ID - Name', e.g. '123 - John Doe'.")
        return redirect(url_for('view_payments'))

    term_id = request.form.get('term_id')
    amount_paid = request.form.get('amount_paid')
    payment_date = request.form.get('payment_date')

    if not term_id or not amount_paid or not payment_date:
        flash("Please fill in all payment fields.")
        return redirect(url_for('view_payments'))

    try:
        amount_paid = float(amount_paid)
    except ValueError:
        flash("Amount paid must be a number.")
        return redirect(url_for('view_payments'))

    # Optional: Validate student_id and term_id exist
    student = query_db('SELECT * FROM students WHERE id = ?', (student_id,), one=True)
    term = query_db('SELECT * FROM terms WHERE id = ?', (term_id,), one=True)
    if not student:
        flash("Student not found.")
        return redirect(url_for('view_payments'))
    if not term:
        flash("Term not found.")
        return redirect(url_for('view_payments'))

    query_db(
        'INSERT INTO payments (student_id, term_id, amount_paid, payment_date) VALUES (?, ?, ?, ?)',
        (student_id, int(term_id), amount_paid, payment_date)
    )
    flash("Payment added successfully.")
    return redirect(url_for('view_payments'))

# Edit Student
@app.route('/student/edit/<int:id>', methods=['POST'])
def edit_student(id):
    name = request.form['name']
    form = request.form['form']
    query_db('UPDATE students SET name=?, form=? WHERE id=?', (name, form, id))
    flash("Student updated successfully.")
    return redirect(url_for('view_students'))

# Delete Student
@app.route('/student/delete/<int:id>', methods=['POST'])
def delete_student(id):
    query_db('DELETE FROM students WHERE id=?', (id,))
    flash("Student deleted successfully.")
    return redirect(url_for('view_students'))

# Edit Term
@app.route('/term/edit/<int:id>', methods=['POST'])
def edit_term(id):
    name = request.form['term_name']
    amount = request.form['amount']
    query_db('UPDATE terms SET name=?, amount=? WHERE id=?', (name, amount, id))
    flash("Term updated successfully.")
    return redirect(url_for('view_terms'))

# Delete Term
@app.route('/term/delete/<int:id>', methods=['POST'])
def delete_term(id):
    query_db('DELETE FROM terms WHERE id=?', (id,))
    flash("Term deleted successfully.")
    return redirect(url_for('view_terms'))

# Edit Payment
@app.route('/payment/edit/<int:id>', methods=['POST'])
def edit_payment(id):
    student_id = request.form['student_id']
    term_id = request.form['term_id']
    amount_paid = request.form['amount_paid']
    payment_date = request.form['payment_date']
    query_db('''
        UPDATE payments SET student_id=?, term_id=?, amount_paid=?, payment_date=?
        WHERE id=?
    ''', (student_id, term_id, amount_paid, payment_date, id))
    flash("Payment updated successfully.")
    return redirect(url_for('view_payments'))

# Delete Payment
@app.route('/payment/delete/<int:id>', methods=['POST'])
def delete_payment(id):
    query_db('DELETE FROM payments WHERE id=?', (id,))
    flash("Payment deleted successfully.")
    return redirect(url_for('view_payments'))

@app.route('/receipt/<int:payment_id>')
def view_receipt(payment_id):
    payment = query_db('''
        SELECT payments.id, students.name AS student_name, students.admission_no,
               students.form, terms.name AS term_name, terms.amount AS term_amount,
               payments.amount_paid, payments.payment_date
        FROM payments
        JOIN students ON payments.student_id = students.id
        JOIN terms ON payments.term_id = terms.id
        WHERE payments.id = ?
    ''', (payment_id,), one=True)

    if not payment:
        return "Receipt not found", 404

    return render_template('receipt.html', payment=payment, current_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
@app.route('/reports/outstanding_balance')
def report_outstanding_balance():
    # Query students, total fees due (sum of all terms), total paid, outstanding
    data = query_db('''
        SELECT 
            students.id,
            students.name,
            students.admission_no,
            IFNULL(SUM(terms.amount), 0) AS total_due,
            IFNULL(SUM(payments.amount_paid), 0) AS total_paid,
            (IFNULL(SUM(terms.amount), 0) - IFNULL(SUM(payments.amount_paid), 0)) AS outstanding_balance
        FROM students
        LEFT JOIN terms ON 1=1
        LEFT JOIN payments ON payments.student_id = students.id AND payments.term_id = terms.id
        GROUP BY students.id
        HAVING outstanding_balance > 0
        ORDER BY outstanding_balance DESC
    ''')
    return render_template('reports_outstanding_balance.html', data=data)

if __name__ == '__main__':
    init_db()
    app.run(debug=True, port=2000)
