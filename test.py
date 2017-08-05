# Python port

# Main loop

while True:
	# display menu
    print('Current source : ${arSource[$iSource]}')
    print('---------------------------------')
    print('1. Next Source')
    print('2. Play / Pause')
    print('3. Next track (USB) / station (Radio)')
    print('4. Prev track (USB) / station (Radio)')
    print('5. Volume up')
    print('6. Volume down')
    print('7. Prev Folder (USB)')
    print('8. Next Folder (USB)')
    print('9. Mode: Shuffle (all) / Normal')
    print('0. Exit')
	print('DEBUG OPTIONS:')
    print('C. check_source')
	print('---------------------------------')
	c = raw_input("Enter your choice [0-9] : ")
	# take action
	if c == '1':
		print('1) source_next')
	elif c == '2':
		print('2) play_pause')
	elif c == '3':
		print('3) next')
	elif c == '4':
		print('4) prev')
	elif c == '5':
		print('5) volume_up')
	elif c == '6':
		print('6) volume_down')
	elif c == '7':
		print('7) mpc_prev_folder')
	elif c == '8':
		print('8) mpc_next_folder')
	elif c == '9':
		print('9) mode_change')
	elif c == 'C':
		print('C) check_source')
	else:
		print('Select between 0 to 8 only')
