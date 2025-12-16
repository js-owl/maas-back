import bcrypt
import sqlite3

user_id = 1

# Assuming 'new_plaintext_password' is the user's new password
new_hashed_password = bcrypt.hashpw('WQu^^^kLNrDDEXBJ#WJT9Z'.encode('utf-8'), bcrypt.gensalt())
print(new_hashed_password)

conn = sqlite3.connect('shop.db')
cursor = conn.cursor()

# old hasinh pass - $2b$12$Mn5LwvJeTI9lxMyvk.L5seSpU7O3FxGo5GJNNNEFS9ye3efCQkR6O
# Assuming 'user_id' is the identifier for the user whose password is being updated
# and 'new_hashed_password' is the result from step 1
update_sql = "UPDATE users SET hashed_password = ? WHERE id = ?"
#update_sql = "SELECT * FROM users"
cursor.execute(update_sql, (new_hashed_password, user_id))
#print(test)

#UPDATE users SET hashed_password = '$2b$12$hC7o716nGVlkogc7eTyVa.E4EYU9G0ikB/WDiulpL.k80e53ciotm' WHERE id = 1;

conn.commit()
conn.close()