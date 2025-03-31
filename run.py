import time

start_time = time.time()
run_duration = 6 * 3600  # 6 ghante seconds me

def main():
    while True:
        elapsed_time = time.time() - start_time
        if elapsed_time >= run_duration:
            print("Script 6 ghante tak chal chuki hai. Exit ho raha hai.")
            break  # 6 ghante ke baad exit

        hours = elapsed_time / 3600
        print(f"Script {hours:.2f} ghante se chal rahi hai.")

        time.sleep(60)  # 60 second wait karega phir dubara chalega

if __name__ == "__main__":  # Ye fix kiya gaya hai
    main()
