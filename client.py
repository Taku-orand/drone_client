#!/usr/bin/env python3
# coding: UTF-8

import cv2
from time import sleep
import struct
import redis
import numpy as np
import json
from sshtunnel import SSHTunnelForwarder

# External variables 
ESC = 27
LEFT_SHIFT = 225
KEY_1 = "1"
WASD = ["w","a","s","d"] 
NUM_0_9 = ["0","1","2","3","4","5","6","7","8","9"]
C_OR_M = ["c","m"]


# get data from redis server and decode JPEG data
def fromRedis(hRedis,topic):
	"""Retrieve Numpy array from Redis key 'topic'"""
	encoded = hRedis.get(topic)
	h, w = struct.unpack('>II',encoded[:8])		# unpack

	# make numpy array
	a = np.frombuffer(encoded, dtype=np.uint8, offset=8)

	# decode jpeg to opencv image
	decimg = cv2.imdecode(a, flags=cv2.IMREAD_UNCHANGED).reshape(h,w,3)

	return decimg

# Main Function
if __name__ == '__main__':
	# Redis connection
	ssht = SSHTunnelForwarder(
        	("163.143.132.153", 22),
        	ssh_host_key=None,
        	ssh_username="uavdata",
        	ssh_password="0158423046",
        	ssh_pkey=None,
        	remote_bind_address=("localhost", 6379))
	ssht.start()
	r = redis.Redis(host='localhost', port=ssht.local_bind_port, db=0)
	r.set('command', '')
	cmd = ''
	show = False		# 「次の操作を待つ」ためのフラグ

	# loop until you press Ctrl+c
	try:
		while True:
			# Topic name of OpenCV image is "image"
			img = fromRedis(r,'image')

			# Topic name of Tello Status is "state"
			json_state = r.get('state')
			dict_state = json.loads( json_state )	# convert to Dictionary
			# print( 'Battery:%d '%(dict_state['bat']) )

			# show OpenCV image
			cv2.imshow('Image from Redis', img)

			# wait key-input 1ms on OpenCV window
			key = cv2.waitKey(1)
				
			if key == ord(KEY_1):		# キーボードの「1」を押すと、距離指定に変更
				print("距離指定に変更")
				print("方向を入力")
				direction = chr(int(cv2.waitKey(0)))
				print("cmかmを入力")
				unit = chr(int(cv2.waitKey(0)))
				print("0~9で入力")
				distance = chr(int(cv2.waitKey(0)))
				print(direction, unit, distance)
    
				show = True
    
				# 期待されない入力は受け付けない(上に記載)
				if direction not in WASD or unit not in C_OR_M or distance not in NUM_0_9:
					print("中止")
					continue

				move_info = direction + str(unit) + str(int(distance))
				r.set('command', move_info)


			if key == ESC:				# exit
				break
			elif key == LEFT_SHIFT:
				r.set('command', '_pause')
				print("停止")
				show = True
			elif key == ord('m'):		# arm throttle
				r.set('command','_arm')	# r.set([Topic],[Payload]) Topic is "command". Payload is SDK command.
				print("プロペラ起動")
				show = True
			elif key == ord('n'):		# disarmed
				r.set('command', '_disarmed')
				print("プロペラ停止")
				show = True
			elif key == ord('t'):		# takeoff
				r.set('command','_takeoff')
				print("離陸中...")
				show = True
			elif key == ord('l'):		# land
				r.set('command','_land')
				print("着陸中...")
				show = True
			elif key == ord('w'):		# forward
				r.set('command','_forward')
				print("前方移動")
				show = True
			elif key == ord('s'):		# back
				r.set('command','_back')
				print("後方移動")
				show = True
			elif key == ord('a'):		# move left
				r.set('command','_left')
				print("左に移動")
				show = True
			elif key == ord('d'):		# move right
				r.set('command','_right')
				print("右に移動")
				show = True
			elif key == ord('q'):		# turn left
				r.set('command','_rotate_left')
				print("左回転")
				show = True
			elif key == ord('e'):		# turn right
				r.set('command','_rotate_right')
				print("右回転")
				show = True
			elif key == ord('r'):		# move up
				r.set('command','_up')
				print("上昇中")
				show = True
			elif key == ord('f'):		# move down
				r.set('command','_down')
				print("降下中")
				show = True

			if(show == True):
				print("次の操作を待っています...")
				show = False

	except( KeyboardInterrupt, SystemExit):    # if Ctrl+c is pressed, quit program.
		print( "Detect SIGINT." )
