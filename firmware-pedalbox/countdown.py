import tkinter as tk
from tkinter import simpledialog
from datetime import datetime, timedelta
import time
import threading

class CountdownTimer:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Countdown Timer")
        self.root.attributes('-fullscreen', True)
        self.root.configure(bg='black')

        # Create label for display
        self.display_label = tk.Label(
            self.root,
            text="",
            font=("Arial", 100, "bold"),
            fg="white",
            bg="black"
        )
        self.display_label.pack(expand=True)

        # Add instructions
        self.instructions = tk.Label(
            self.root,
            text="Press ESC to exit\nPress F to toggle fullscreen",
            font=("Arial", 20),
            fg="white",
            bg="black"
        )
        self.instructions.pack(side=tk.BOTTOM, pady=20)

        # Bind keys
        self.root.bind('<Escape>', self.exit_fullscreen)
        self.root.bind('<Key-f>', self.toggle_fullscreen)

        self.finish_time = None

    def get_finish_date(self):
        """Get finish date from user"""
        try:
            date_str = simpledialog.askstring(
                "Finish Date",
                "Enter finish date and time (YYYY-MM-DD HH:MM:SS):\nExample: 2026-12-31 23:59:59"
            )
            if date_str:
                return datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
            else:
                return datetime.now() + timedelta(weeks=1)
        except ValueError:
            print("Invalid date format. Using default 1 week from now.")
            return datetime.now() + timedelta(weeks=1)

    def calculate_time_left(self, end_time):
        """Calculate time remaining until end_time"""
        now = datetime.now()
        if end_time > now:
            diff = end_time - now
            days = diff.days
            hours, remainder = divmod(diff.seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            return days, hours, minutes, seconds
        else:
            return 0, 0, 0, 0

    def update_display(self):
        """Update the display with remaining time"""
        if self.finish_time:
            days_left, hours_left, minutes_left, seconds_left = self.calculate_time_left(self.finish_time)

            # Format string as days:hours:minutes:seconds
            time_text = f"{days_left:03d}:{hours_left:02d}:{minutes_left:02d}:{seconds_left:02d}"
            self.display_label.config(text=time_text)

    def run(self):
        """Start the timer"""
        # Get finish date and time from user
        self.finish_time = self.get_finish_date()

        def update_loop():
            while True:
                self.update_display()
                self.root.update_idletasks()
                self.root.update()
                time.sleep(1)

        # Start update loop in a separate thread
        update_thread = threading.Thread(target=update_loop, daemon=True)
        update_thread.start()

        try:
            self.root.mainloop()
        except KeyboardInterrupt:
            print("Timer stopped.")

    def exit_fullscreen(self, event=None):
        """Exit fullscreen mode"""
        self.root.destroy()

    def toggle_fullscreen(self, event=None):
        """Toggle fullscreen mode"""
        current_state = self.root.attributes('-fullscreen')
        self.root.attributes('-fullscreen', not current_state)

def main():
    timer = CountdownTimer()
    timer.run()

if __name__ == "__main__":
    main()
