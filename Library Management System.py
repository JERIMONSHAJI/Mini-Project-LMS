import sqlite3
from datetime import date

DB = "library.db"


# DATABASE
def database():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
                 id INTEGER PRIMARY KEY AUTOINCREMENT,
                 uid TEXT UNIQUE NOT NULL,
                 username TEXT NOT NULL,
                 password TEXT NOT NULL,
                 role TEXT NOT NULL CHECK(role IN ('Student','Assistant','Librarian'))
                 )''')
    c.execute('''CREATE TABLE IF NOT EXISTS books (
                 id INTEGER PRIMARY KEY AUTOINCREMENT,
                 code TEXT UNIQUE NOT NULL,
                 title TEXT NOT NULL,
                 author TEXT NOT NULL,
                 isbn TEXT,
                 category TEXT NOT NULL,
                 total_copies INTEGER DEFAULT 1,
                 available_copies INTEGER DEFAULT 1
                 )''')
    c.execute('''CREATE TABLE IF NOT EXISTS borrow (
                 id INTEGER PRIMARY KEY AUTOINCREMENT,
                 book_id INTEGER,
                 user_id INTEGER,
                 borrow_date TEXT DEFAULT (date('now')),
                 return_date TEXT,
                 FOREIGN KEY(book_id) REFERENCES books(id),
                 FOREIGN KEY(user_id) REFERENCES users(id)
                 )''')
    conn.commit()
    conn.close()


def db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn


def has_librarian():
    conn = db()
    c = conn.cursor()
    c.execute("SELECT 1 FROM users WHERE role='Librarian' LIMIT 1")
    exists = c.fetchone() is not None
    conn.close()
    return exists


# BOOK CODE
def generate_book_code():
    conn = db()
    c = conn.cursor()
    c.execute("SELECT code FROM books ORDER BY id DESC LIMIT 1")
    last = c.fetchone()
    conn.close()
    if not last:
        return "BOOK001"
    num = int(last['code'].replace("BOOK", ""))
    return f"BOOK{str(num + 1).zfill(3)}"


# ADD BOOK
def add_book():
    print("\n=== ADD NEW BOOK ===")
    title = input("Title: ").strip()
    author = input("Author: ").strip()
    isbn = input("ISBN (optional): ").strip()
    category = input("Category: ").strip()
    copies = input("Number of Copies: ").strip()
    if not copies.isdigit() or int(copies) < 1:
        print("Invalid number!")
        return
    copies = int(copies)
    code = generate_book_code()
    conn = db()
    conn.execute("""INSERT INTO books 
                    (code, title, author, isbn, category, total_copies, available_copies) 
                    VALUES (?,?,?,?,?,?,?)""",
                 (code, title, author, isbn or "", category, copies, copies))
    conn.commit()
    conn.close()
    print(f"\nBook Added!")
    print(f"Code: {code} | Total: {copies} | Available: {copies}")


# VIEW BOOKS
def view_books():
    conn = db()
    c = conn.cursor()
    c.execute("SELECT id, code, title, author, category, total_copies, available_copies FROM books")
    books = c.fetchall()
    conn.close()
    if not books:
        print("\nNo books in library.")
        return
    print("\n" + "═" * 90)
    print(f"{'ID':<3} {'CODE':<8} {'TITLE':<25} {'AUTHOR':<15} {'CAT':<10} {'TOTAL':<6} {'AVAIL'}")
    print("─" * 90)
    for b in books:
        status = "AVAILABLE" if b['available_copies'] > 0 else "NONE LEFT"
        print(
            f"{b['id']:<3} {b['code']:<8} {b['title'][:24]:<25} {b['author'][:14]:<15} {b['category'][:9]:<10} {b['total_copies']:<6} {b['available_copies']} → {status}")
    print("═" * 90)


# VIEW BORROWED BOOKS
def view_borrowed():
    conn = db()
    c = conn.cursor()
    c.execute('''SELECT borrow.id, books.code, books.title, users.uid, users.username, 
                        borrow.borrow_date, borrow.return_date
                 FROM borrow
                 JOIN books ON borrow.book_id = books.id
                 JOIN users ON borrow.user_id = users.id
                 ORDER BY borrow.borrow_date DESC''')
    records = c.fetchall()
    conn.close()

    if not records:
        print("\nNo borrowed books.")
        return

    print("\n" + "═" * 100)
    print(f"{'ID':<4} {'CODE':<8} {'TITLE':<22} {'STUDENT':<12} {'BORROWED':<12} {'RETURNED'}")
    print("─" * 100)
    for r in records:
        returned = r['return_date'] if r['return_date'] else "Not Returned"
        print(f"{r['id']:<4} {r['code']:<8} {r['title'][:21]:<22} {r['uid']:<12} {r['borrow_date']:<12} {returned}")
    print("═" * 100)


# BORROW BOOK
def borrow_book(user):
    view_books()
    code = input("\nEnter Book CODE to borrow: ").strip().upper()
    conn = db()
    c = conn.cursor()
    c.execute("SELECT id, available_copies, title FROM books WHERE code=?", (code,))
    book = c.fetchone()
    if not book:
        print("Book not found!")
        conn.close()
        return
    if book['available_copies'] <= 0:
        print("No copies available!")
        conn.close()
        return
    c.execute("UPDATE books SET available_copies = available_copies - 1 WHERE id=?", (book['id'],))
    c.execute("INSERT INTO borrow (book_id, user_id) VALUES (?,?)", (book['id'], user['id']))
    conn.commit()
    conn.close()
    print(f"\nBorrowed: {book['title']}")
    print(f"Remaining copies: {book['available_copies'] - 1}")


# RETURN BOOK
def return_book(user):
    conn = db()
    c = conn.cursor()
    c.execute('''SELECT borrow.id, books.code, books.title 
                 FROM borrow 
                 JOIN books ON borrow.book_id = books.id 
                 WHERE borrow.user_id = ? AND return_date IS NULL''', (user['id'],))
    book = c.fetchall()
    conn.close()

    if not book:
        print("\nYou have no borrowed books.")
        return

    print("\nYour Borrowed Books:")
    for l in book:
        print(f"→ ID: {l['id']} | {l['code']} | {l['title']}")

    bid = input("\nEnter Borrow ID to return: ").strip()

    if not bid.isdigit():
        print("Invalid ID! Please enter a valid number.")
        return

    bid = int(bid)

    conn = db()
    c = conn.cursor()
    c.execute("SELECT 1 FROM borrow WHERE id=? AND user_id=? AND return_date IS NULL", (bid, user['id']))
    if not c.fetchone():
        print("Invalid ID! This book is not borrowed by you or already returned.")
        conn.close()
        return

    # Now safely return
    c.execute("UPDATE borrow SET return_date = date('now') WHERE id=?", (bid,))
    c.execute("UPDATE books SET available_copies = available_copies + 1 WHERE id = (SELECT book_id FROM borrow WHERE id=?)", (bid,))
    conn.commit()
    conn.close()

    print("Book returned successfully! Thank you")


# USER MANAGEMENT
def register_librarian():
    print("\n" + "=" * 50)
    print("   FIRST-TIME LIBRARIAN REGISTRATION")
    print("=" * 50)
    uid = input("Librarian ID (LIB001): ").strip().upper()
    username = input("Username: ").strip()
    password = input("Password: ").strip()
    confirm = input("Confirm Password: ").strip()
    if password != confirm:
        print("Passwords do not match!")
        return False
    conn = db()
    c = conn.cursor()
    try:
        c.execute("INSERT INTO users (uid,username,password,role) VALUES (?,?,?,?)",
                  (uid, username, password, "Librarian"))
        conn.commit()
        print(f"Librarian registered! → {uid}")
        return True
    except:
        print("UID or Username taken!")
        return False
    finally:
        conn.close()


def add_assistant():
    print("\n" + "=" * 40)
    print("   ADD NEW ASSISTANT (Librarian Only)")
    print("=" * 40)
    uid = input("Assistant ID (AST001): ").strip().upper()
    username = input("Username: ").strip()
    password = input("Password: ").strip()
    confirm = input("Confirm Password: ").strip()
    if password != confirm:
        print("Passwords do not match!")
        return
    conn = db()
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE uid=?", (uid,))
    if c.fetchone():
        print("This ID is already registered!")
        conn.close()
        return
    c.execute("INSERT INTO users (uid,username,password,role) VALUES (?,?,?,?)",
              (uid, username, password, "Assistant"))
    conn.commit()
    conn.close()
    print(f"Assistant added! → {uid}")


def view_assistant():
    conn = db()
    c = conn.cursor()
    c.execute('''SELECT * FROM users WHERE role="Assistant"''')
    assistant=c.fetchall()
    conn.close()
    if not assistant:
        print("\nYou have no registered Assistants.")
        return
    print("\nID  UID       USERNAME          ROLE")
    print("-" * 40)
    for a in assistant:
        print(f"{a['id']:<3} {a['uid']:<10} {a['username']:<17} {a['role']}")


def register_student():
    print("\n=== REGISTER NEW STUDENT ===")
    uid = input("Student ID (STU101): ").strip().upper()
    username = input("Username: ").strip()
    password = input("Password: ").strip()
    confirm = input("Confirm Password: ").strip()
    if password != confirm:
        print("Passwords do not match!")
        return
    conn = db()
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE uid=?", (uid,))
    if c.fetchone():
        print("This ID is already registered!")
        conn.close()
        return
    c.execute("INSERT INTO users (uid,username,password,role) VALUES (?,?,?,?)",
              (uid, username, password, "Student"))
    conn.commit()
    conn.close()
    print(f"Student registered! → {uid}")


def view_student():
    conn = db()
    c = conn.cursor()
    c.execute('''SELECT * FROM users WHERE role="Student"''')
    student = c.fetchall()
    conn.close()
    if not student:
        print("\nYou have no registered Students.")
        return
    print("\nID  UID       USERNAME          ROLE")
    print("-" * 40)
    for s in student:
        print(f"{s['id']:<3} {s['uid']:<10} {s['username']:<17} {s['role']}")


def login():
    print("\n=== LOGIN ===")
    uid = input("Enter Your ID: ").strip()
    password = input("Password: ").strip()
    conn = db()
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE uid=? AND password=?", (uid, password))
    user = c.fetchone()
    conn.close()
    if user:
        print(f"\nWelcome, {user['username']} | {user['uid']} ({user['role']})")
        return user
    print("Wrong ID or password!")
    return None


def del_book():
    view_books()
    bid = input("\nEnter Book ID to delete: ").strip()
    if not bid.isdigit():
        print("Invalid ID.")
        return
    conn = db()
    c = conn.cursor()
    c.execute("DELETE FROM books WHERE id=?", (bid,))
    conn.commit()
    conn.close()
    print("Book deleted!" if c.rowcount else "Not found.")


def del_user():
    conn = db()
    c = conn.cursor()
    c.execute("SELECT id, uid, username, role FROM users WHERE role != 'Librarian'")
    users = c.fetchall()
    conn.close()
    if not users:
        print("No one to delete.")
        return
    print("\nID  UID       USERNAME          ROLE")
    print("-" * 40)
    for u in users:
        print(f"{u['id']:<3} {u['uid']:<10} {u['username']:<17} {u['role']}")
    uid = input("\nEnter User ID to delete: ").strip()
    conn = db()
    c = conn.cursor()
    c.execute("DELETE FROM users WHERE id=? AND role != 'Librarian'", (uid,))
    conn.commit()
    conn.close()
    print("User deleted!" if c.rowcount else "Invalid / Protected.")


# MENUS
def librarian_menu():
    while True:
        print("\n=== LIBRARIAN DASHBOARD ===")
        print("1. Add Book")
        print("2. Delete Book")
        print("3. Add Assistant")
        print("4. Add Student")
        print("5. Delete User")
        print("6. View Books")
        print("7. View Borrowed Books")
        print("8. View Assistant")
        print("9. View Student")
        print("10. Logout")
        ch = input("Choose (1-10): ").strip()
        if ch == '1':
            add_book()
        elif ch == '2':
            del_book()
        elif ch == '3':
            add_assistant()
        elif ch == '4':
            register_student()
        elif ch == '5':
            del_user()
        elif ch == '6':
            view_books()
        elif ch == '7':
            view_borrowed()
        elif ch == '8':
            view_assistant()
        elif ch == '9':
            view_student()
        elif ch == '10':
            break
        else:
            print("Invalid input.")


def assistant_menu():
    while True:
        print("\n=== ASSISTANT DASHBOARD ===")
        print("1. Add Book")
        print("2. Delete Book")
        print("3. View Books")
        print("4. View Borrowed Books")
        print("5. View Student")
        print("6. Logout")
        ch = input("Choose (1-6): ").strip()
        if ch == '1':
            add_book()
        elif ch == '2':
            del_book()
        elif ch == '3':
            view_books()
        elif ch == '4':
            view_borrowed()
        elif ch == '5':
            view_student()
        elif ch == '6':
            break
        else:
            print("Invalid input.")


def student_menu(user):
    while True:
        print("\n=== STUDENT DASHBOARD ===")
        print("1. View All Books")
        print("2. Borrow Book")
        print("3. Return Book")
        print("4. Logout")
        ch = input("Choose (1-4): ").strip()
        if ch == '1':
            view_books()
        elif ch == '2':
            borrow_book(user)
        elif ch == '3':
            return_book(user)
        elif ch == '4':
            print("Logged out safely.")
            break
        else:
            print("Invalid input.")


# MAIN
def main():
    database()
    print("\n" + "=" * 50)
    print("   LIBRARY MANAGEMENT SYSTEM")
    print("=" * 50)

    if not has_librarian():
        print("No Librarian found!")
        if input("Register first Librarian? (y/n): ").lower() == 'y':
            register_librarian()
        else:
            print("System requires a Librarian.")
            return

    while True:
        print("\n1. Login")
        print("2. Register Student")
        print("3. Exit")
        choice = input("Choose (1-3): ").strip()
        if choice == '1':
            user = login()
            if not user:
                continue
            if user['role'] == 'Librarian':
                librarian_menu()
            elif user['role'] == 'Assistant':
                assistant_menu()
            elif user['role'] == 'Student':
                student_menu(user)
        elif choice == '2':
            register_student()
        elif choice == '3':
            print("Thank you! Goodbye ")
            break
        else:
            print("Invalid choice.")


if __name__ == "__main__":
    main()