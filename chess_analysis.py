#!/usr/bin/env python3
import subprocess
import sys
import time
import threading
import os
from datetime import datetime

class StockfishTerminal:
    def __init__(self, path_to_stockfish="stockfish"):
        """Initialize the Stockfish engine process."""
        try:
            # Start Stockfish as a subprocess
            self.process = subprocess.Popen(
                path_to_stockfish,
                universal_newlines=True,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            # Initialize state variables
            self.is_ready = False
            self.position = "startpos"
            self.white_time = 600  # 10 minutes in seconds
            self.black_time = 600
            self.increment = 0
            self.current_player = "white"
            self.timer_running = False
            self.timer_thread = None
            
            # Send UCI command to initialize the engine
            self._send_command("uci")
            self._wait_for_uciok()
            
            # Set up initial parameters
            self._send_command("isready")
            self._wait_for_readyok()
            self.is_ready = True
            
            print("Stockfish engine initialized successfully.")
        except Exception as e:
            print(f"Error initializing Stockfish: {e}")
            sys.exit(1)
    
    def _send_command(self, command):
        """Send a command to the Stockfish engine."""
        try:
            self.process.stdin.write(command + "\n")
            self.process.stdin.flush()
        except Exception as e:
            print(f"Error sending command: {e}")
    
    def _get_output(self, timeout=0.1):
        """Get output from the Stockfish engine."""
        output_lines = []
        start_time = time.time()
        
        while True:
            # Check if there's any output available
            if self.process.stdout.readable():
                line = self.process.stdout.readline().strip()
                if line:
                    output_lines.append(line)
                    # If we see bestmove, we're done
                    if line.startswith("bestmove"):
                        break
            
            # Check if we've exceeded the timeout
            if timeout and time.time() - start_time > timeout:
                break
            
            # Small sleep to avoid tight loop
            time.sleep(0.01)
        
        return output_lines
    
    def _wait_for_uciok(self):
        """Wait for the 'uciok' response from the engine."""
        while True:
            line = self.process.stdout.readline().strip()
            if line == "uciok":
                return
    
    def _wait_for_readyok(self):
        """Wait for the 'readyok' response from the engine."""
        while True:
            line = self.process.stdout.readline().strip()
            if line == "readyok":
                return
    
    def set_position(self, moves=None, fen=None):
        """Set the current position using moves or FEN notation."""
        if fen:
            self.position = f"fen {fen}"
        else:
            self.position = "startpos"
        
        position_command = f"position {self.position}"
        
        if moves:
            if isinstance(moves, list):
                moves_str = " ".join(moves)
            else:
                moves_str = moves
            position_command += f" moves {moves_str}"
        
        self._send_command(position_command)
        print(f"Position set: {position_command}")
    
    def get_best_move(self, depth=15, movetime=None):
        """Get the best move for the current position."""
        # Make sure the engine is ready
        self._send_command("isready")
        self._wait_for_readyok()
        
        # Prepare go command
        go_command = "go"
        if depth:
            go_command += f" depth {depth}"
        if movetime:
            go_command += f" movetime {movetime}"
        
        # Send the command
        self._send_command(go_command)
        
        # Collect output until we get the best move
        output = []
        best_move = None
        
        while True:
            line = self.process.stdout.readline().strip()
            output.append(line)
            
            if line.startswith("bestmove"):
                best_move = line.split()[1]
                break
        
        # Print the analysis
        for line in output:
            if line.startswith("info") and "pv" in line:
                parts = line.split()
                try:
                    depth_index = parts.index("depth")
                    score_index = parts.index("score")
                    pv_index = parts.index("pv")
                    
                    depth_value = parts[depth_index + 1]
                    score_type = parts[score_index + 1]
                    score_value = parts[score_index + 2]
                    pv_moves = " ".join(parts[pv_index + 1:])
                    
                    print(f"Depth {depth_value} | Score {score_type} {score_value} | Line: {pv_moves}")
                except (ValueError, IndexError):
                    pass
        
        return best_move
    
    def _timer_loop(self):
        """Timer loop to count down player time."""
        last_time = time.time()
        
        while self.timer_running:
            current_time = time.time()
            elapsed = current_time - last_time
            last_time = current_time
            
            if self.current_player == "white":
                self.white_time -= elapsed
                if self.white_time <= 0:
                    self.white_time = 0
                    self.timer_running = False
                    print("\nWhite's time has expired! Black wins on time.")
            else:
                self.black_time -= elapsed
                if self.black_time <= 0:
                    self.black_time = 0
                    self.timer_running = False
                    print("\nBlack's time has expired! White wins on time.")
            
            # Update time display every second
            time.sleep(0.1)
    
    def start_timer(self):
        """Start the chess clock."""
        if not self.timer_running:
            self.timer_running = True
            self.timer_thread = threading.Thread(target=self._timer_loop)
            self.timer_thread.daemon = True
            self.timer_thread.start()
            print(f"Timer started. {self.current_player.capitalize()}'s move.")
    
    def stop_timer(self):
        """Stop the chess clock."""
        self.timer_running = False
        if self.timer_thread:
            self.timer_thread.join(timeout=1.0)
        print("Timer stopped.")
    
    def switch_player(self):
        """Switch active player and apply increment."""
        if self.current_player == "white":
            self.white_time += self.increment
            self.current_player = "black"
        else:
            self.black_time += self.increment
            self.current_player = "white"
        
        print(f"Now {self.current_player.capitalize()}'s turn.")
        self._display_times()
    
    def set_time_control(self, minutes, increment_seconds=0):
        """Set a new time control."""
        self.white_time = minutes * 60
        self.black_time = minutes * 60
        self.increment = increment_seconds
        print(f"Time control set to {minutes} minutes with {increment_seconds} second increment.")
        self._display_times()
    
    def _format_time(self, seconds):
        """Format time as MM:SS."""
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes:02d}:{secs:02d}"
    
    def _display_times(self):
        """Display current time for both players."""
        white_formatted = self._format_time(self.white_time)
        black_formatted = self._format_time(self.black_time)
        print(f"White: {white_formatted} | Black: {black_formatted}")
    
    def close(self):
        """Close the Stockfish engine."""
        if self.process:
            self._send_command("quit")
            self.process.terminate()
            print("Stockfish engine closed.")


def print_help():
    """Print help information."""
    print("\nStockfish Terminal Interface - Available Commands:")
    print("-" * 50)
    print("help                          - Show this help message")
    print("set position [moves]          - Set position with optional moves (e.g., 'set position e2e4 e7e5')")
    print("set fen [fen_string]          - Set position using FEN notation")
    print("set time [minutes] [increment]- Set time control (e.g., 'set time 5 2' for 5 min + 2 sec)")
    print("best [depth]                  - Get best move with optional depth (default: 15)")
    print("go [movetime_ms]              - Get best move with optional time limit in milliseconds")
    print("start                         - Start the chess clock")
    print("stop                          - Stop the chess clock")
    print("switch                        - Switch the active player and apply increment")
    print("times                         - Display current times")
    print("quit                          - Exit the program")
    print("-" * 50)


def main():
    """Main function to run the terminal interface."""
    # Get Stockfish path from command line or use default
    stockfish_path = sys.argv[1] if len(sys.argv) > 1 else "stockfish"
    
    try:
        # Create Stockfish interface
        chess_engine = StockfishTerminal(stockfish_path)
        
        print("\nStockfish Terminal Interface")
        print("Type 'help' for available commands")
        
        # Main command loop
        while True:
            try:
                user_input = input("\n> ").strip()
                
                if not user_input:
                    continue
                
                cmd_parts = user_input.split()
                command = cmd_parts[0].lower()
                
                if command == "quit" or command == "exit":
                    break
                
                elif command == "help":
                    print_help()
                
                elif command == "set":
                    if len(cmd_parts) < 2:
                        print("Error: Invalid set command. Try 'set position', 'set fen', or 'set time'.")
                        continue
                    
                    set_command = cmd_parts[1].lower()
                    
                    if set_command == "position":
                        moves = cmd_parts[2:] if len(cmd_parts) > 2 else None
                        chess_engine.set_position(moves)
                    
                    elif set_command == "fen":
                        if len(cmd_parts) < 3:
                            print("Error: FEN string required.")
                            continue
                        fen = " ".join(cmd_parts[2:])
                        chess_engine.set_position(fen=fen)
                    
                    elif set_command == "time":
                        if len(cmd_parts) < 3:
                            print("Error: Time in minutes required.")
                            continue
                        
                        try:
                            minutes = int(cmd_parts[2])
                            increment = int(cmd_parts[3]) if len(cmd_parts) > 3 else 0
                            chess_engine.set_time_control(minutes, increment)
                        except ValueError:
                            print("Error: Invalid time values.")
                    
                    else:
                        print(f"Error: Unknown set command '{set_command}'.")
                
                elif command == "best":
                    depth = int(cmd_parts[1]) if len(cmd_parts) > 1 else 15
                    best_move = chess_engine.get_best_move(depth=depth)
                    print(f"Best move: {best_move}")
                
                elif command == "go":
                    movetime = int(cmd_parts[1]) if len(cmd_parts) > 1 else None
                    best_move = chess_engine.get_best_move(movetime=movetime)
                    print(f"Best move: {best_move}")
                
                elif command == "start":
                    chess_engine.start_timer()
                
                elif command == "stop":
                    chess_engine.stop_timer()
                
                elif command == "switch":
                    chess_engine.switch_player()
                
                elif command == "times":
                    chess_engine._display_times()
                
                else:
                    print(f"Unknown command: '{command}'. Type 'help' for available commands.")
            
            except Exception as e:
                print(f"Error: {e}")
        
        # Clean up
        chess_engine.stop_timer()
        chess_engine.close()
        print("Goodbye!")
    
    except Exception as e:
        print(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()