from helping_page import *


def calculate_last_month_consumption(engine):
    last_month = str(datetime.now().month - 1) if datetime.now().month > 1 else '12'
    chat_id_consumption_list = []

    with engine.connect() as conn:
        query = text(f"SELECT chat_id, name, `{last_month}` FROM chat_id_parameters WHERE chat_id IS NOT NULL ORDER BY `{last_month}` DESC")
        df = pd.read_sql(query, conn)
        if df.empty: return "Failed to get the consumption data."
        total_spent = df[last_month].sum().round(3)
        for index, row in df.iterrows():
            if row[last_month] == 0: continue
            if not row['name']: continue
            consumption_value = round(row[last_month], 3)
            inform_string = f"{index+1}. {row['name'].capitalize()} >> {consumption_value} usd"
            chat_id_consumption_list.append(inform_string)
    if chat_id_consumption_list: 
        prefix = f"Total spent in month {last_month} is {total_spent} usd.\n"
        chat_id_consumption_list.insert(0, prefix)
        send_message(OWNER_CHAT_ID, '\n'.join(chat_id_consumption_list), TELEGRAM_BOT_TOKEN)
    else: send_message(OWNER_CHAT_ID, f"No consumption data found for month {last_month}", TELEGRAM_BOT_TOKEN)
    return


def reset_current_month_consumption(engine):
    try:
        # Get the current month as an integer (1-12), and convert to string for the column name
        current_month = str(datetime.now().month)
        with engine.begin() as conn:
            # SQL query to set the value of the current month column to 0 for all records
            reset_query = f"""
            UPDATE chat_id_parameters
            SET `{current_month}` = 0
            """
            # Execute the reset query
            conn.execute(text(reset_query))
            logging.info(f"Successfully reset consumption values for month: {current_month}")
    except Exception as e: logging.exception(f"Failed to reset monthly consumption: {e}")
    return


if __name__ == "__main__":
    engine = get_engine()
    reset_current_month_consumption(engine)
    calculate_last_month_consumption(engine)