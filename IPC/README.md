# Milestone 2 - Part 1
# Group 11 Reza Amraei, Christopher Ascencio, Eduardo Martinez, Dylan Peacock, Duy Phung

# Description
The following files simulate the TCP and UDP connections feature of a 4-player multiplayer game built using Python and pipes

# Requirements
Terminal
Python

# Instructions

# Part One - TCP
Files - server.py, sensor.py

Open your terminal.
Start the server: 				python server.py
In another terminal, start a sensor: 		python sensor.py S-001
You can run more sensors in more terminals including S-002 or S-003.

# Part Two - UDP (Optional)
Files - server_udp.py, sensor_udp.py

Open your terminal.
Start the UDP server: 				python server_udp.py
In another terminal, start a sensor: 		python sensor_udp.py U-001
You can run more sensors in more terminals including U-002 or U-003.

# Part Three - Pipes (Optional)
Files - pipe_reader.py, pipe_writer.py

Mac or Linux:
Open your terminal.
Start the reader: 				python pipe_reader.py
In another terminal, start the writer: 		python pipe_writer.py

Windows:
os.mkfifo is not available on Windows. You must use multiprocessing.Pipe to fix this.



