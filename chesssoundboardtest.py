import sounddevice as sd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import queue
import time

# --- Settings ---
DURATION_TO_HOLD = 3  # seconds
MAX_SELECTION_TIME = 20  # max seconds per selection
ROWS = ['8', '7', '6', '5', '4', '3', '2', '1']
COLS = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H']
volume_queue = queue.Queue()

# --- State Variables ---
state = "row"
selected_row = None
selected_col = None
start_time = None
hold_start_time = None
last_zone = None
selection_timer_start = None
selection_stage = 0  # 0 = first select, 1 = second select
pawn_pos = None
pawn_target = None

# --- Audio Callback ---
def callback(indata, frames, time_info, status):
    volume_norm = np.linalg.norm(indata) * 10
    volume = min(volume_norm / 10.0, 1.0)
    volume_queue.put(volume)

# --- Create GUI ---
fig = plt.figure(figsize=(8, 9))
gs = fig.add_gridspec(2, 2, width_ratios=[1, 8], height_ratios=[8, 1])
ax_board = fig.add_subplot(gs[0, 1])
ax_col_volume = fig.add_subplot(gs[0, 0])
ax_row_volume = fig.add_subplot(gs[1, 1])

# Column volume bar (vertical - now for column)
col_bar = ax_col_volume.bar([0], [0], width=0.5, color='blue')[0]
ax_col_volume.set_ylim(0, 1)
ax_col_volume.set_xlim(-0.5, 0.5)
ax_col_volume.set_xticks([])
ax_col_volume.set_yticks([0, 0.5, 1])
ax_col_volume.set_title("Column Volume")

# Row volume bar (horizontal - now for row, growing left to right)
row_bar = ax_row_volume.barh([0], [0], height=0.5, color='blue')[0]
ax_row_volume.set_xlim(0, 1)
ax_row_volume.set_ylim(-0.5, 0.5)
ax_row_volume.set_xticks([0, 0.5, 1])
ax_row_volume.set_yticks([])
ax_row_volume.set_title("Row Volume")

# Chessboard
def draw_board(selected_square=None, highlight_coords=None, pawn_pos=None, pawn_target=None):
    ax_board.clear()
    colors = ['#F0D9B5', '#B58863']
    for row in range(8):
        for col in range(8):
            color = colors[(row + col) % 2]
            rect = patches.Rectangle((col, row), 1, 1, facecolor=color)
            ax_board.add_patch(rect)

    if highlight_coords:
        col_index, row_index = highlight_coords
        highlight = patches.Rectangle((col_index, row_index), 1, 1, facecolor='yellow', alpha=0.3)
        ax_board.add_patch(highlight)

    if pawn_pos:
        col_index = COLS.index(pawn_pos[0])
        row_index = ROWS.index(pawn_pos[1])
        pawn = patches.Circle((col_index + 0.5, row_index + 0.5), 0.3, color='black')
        ax_board.add_patch(pawn)

    if pawn_target:
        col_index = COLS.index(pawn_target[0])
        row_index = ROWS.index(pawn_target[1])
        pawn = patches.Circle((col_index + 0.5, row_index + 0.5), 0.3, color='black')
        ax_board.add_patch(pawn)

    ax_board.set_xlim(0, 8)
    ax_board.set_ylim(0, 8)
    ax_board.set_xticks(np.arange(8) + 0.5)
    ax_board.set_yticks(np.arange(8) + 0.5)
    ax_board.set_xticklabels(COLS)
    ax_board.set_yticklabels(ROWS)
    ax_board.set_title("Chessboard: Select by Volume")
    ax_board.invert_yaxis()
    ax_board.set_aspect('equal')
    ax_board.grid(False)

# --- Main Logic ---
print("Start by selecting a ROW using your volume level...")
draw_board()
plt.ion()
plt.show()

row_index = None
col_index = None

with sd.InputStream(callback=callback):
    while True:
        try:
            volume = volume_queue.get_nowait()
        except queue.Empty:
            volume = 0

        if state == "row":
            row_bar.set_width(volume)
            col_bar.set_height(0)
        else:
            col_bar.set_height(volume)
            row_bar.set_width(0)

        current_time = time.time()
        if selection_timer_start is None:
            selection_timer_start = current_time

        # Timeout after max time
        if current_time - selection_timer_start > MAX_SELECTION_TIME:
            print("Selection timed out. Restarting...")
            break

        if state == "row":
            row_index = int((1 - volume) * len(ROWS))
            row_index = min(row_index, len(ROWS) - 1)
            current_zone = ROWS[row_index]
        else:
            col_index = int(volume * len(COLS))
            col_index = min(col_index, len(COLS) - 1)
            current_zone = COLS[col_index]

        if current_zone != last_zone:
            hold_start_time = current_time
            last_zone = current_zone
        else:
            if hold_start_time and (current_time - hold_start_time >= DURATION_TO_HOLD):
                if state == "row":
                    selected_row = current_zone
                    print(f"Row selected: {selected_row}")
                    state = "col"
                    hold_start_time = None
                    last_zone = None
                    selection_timer_start = None
                    print("Now select a COLUMN using volume...")
                    time.sleep(1)
                elif state == "col":
                    selected_col = current_zone
                    square = selected_col + selected_row
                    print(f"Final Square Selected: {square}")
                    if selection_stage == 0:
                        pawn_pos = square
                        selection_stage = 1
                        state = "row"
                        hold_start_time = None
                        last_zone = None
                        selection_timer_start = None
                        print("Now select destination ROW for the pawn...")
                        time.sleep(1)
                    else:
                        pawn_target = square
                        print("Pawn moved.")
                        break

        highlight_coords = (col_index if col_index is not None else 0,
                            row_index if row_index is not None else 0)
        draw_board(selected_square=None, highlight_coords=highlight_coords, pawn_pos=pawn_pos, pawn_target=None)
        fig.canvas.draw()
        fig.canvas.flush_events()
        time.sleep(0.005)

# Final board with pawn at target
draw_board(pawn_pos=None, pawn_target=pawn_target)    
plt.ioff()
plt.show()
print("Program finished.")