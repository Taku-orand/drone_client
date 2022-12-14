#!/usr/bin/env python3
# coding: UTF-8

import cv2
from time import sleep
import struct
import redis
import numpy as np
import json
from sshtunnel import SSHTunnelForwarder
import sys
import os

# External variables 
ESC     = 27
TAB     = 9
L_SHIFT = 225
KEY_1   = "1"
KEY_2   = "2"
KEY_3   = "3"
WASD    = ["w","a","s","d"] 
QE      = ["q","e"]
RF      = ["r", "f"]
C_OR_M  = ["cm","m"]

MANUAL_MSG = """
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
操作方法
- - - - - - - - - - - - - - - - - - - - - - - - - - - - 
<キーボード>
	1 2 3
tab	q w e r t	 p
	a s d f		l
shift
- - - - - - - - - - - - - - - - - - - - - - - - - - - -
<詳細>
	1: 距離指定(terminalで操作)
	2: 角度指定(terminalで操作)
	3: 上昇/下降距離指定(terminalで操作)
      q/e: 左/右回転
  w/a/s/d: 前/左/後ろ/右移動
      r/f: 上昇/下降
        t: 離陸
        l: 着陸
shift/tab: 移動停止
	p: 操作方法表示

※ Ctrl-cで終了
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
"""

DISTANCE_MODE_MSG = """
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
方向> w(前) a(左) s(後ろ) d(右) を指定
単位> cm か m を指定
距離> 距離を指定(数字のみ) 例) 9

※ 中止する場合、x と入力し続けてください
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
"""

ANGLE_MODE_MSG = """
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
方向> q(左) e(右) を指定
角度> 距離を指定(-:左, +:右) 例) 90→右回転90度, -45→左回転45度

※ 中止する場合、x と入力し続けてください
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
"""

VERTICAL_MODE_MSG = """
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
方向> 上昇(r) 下降(f) を指定
単位> cm か m を指定
距離> 距離を指定(現在地の高度からの距離) 例) 3

※ 中止する場合、x と入力し続けてください
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
"""

def timer(time):
	for i in range(time,-1,-1):
		s = str(i)
		sys.stdout.write("残り \033[2K\033[G%s秒 お待ちください" % s)
		sys.stdout.flush()
		sleep(1)
	print()

def is_num(parameter):
	try:
		float(parameter)
	except:
		return False
	return True


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
	show = False		# 「次の操作を待つ」を表示するためのフラグ

	print(MANUAL_MSG)
	print("操作を待っています")

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
			cv2.imshow('Drone Camera', img)

			# wait key-input 1ms on OpenCV window
			key = cv2.waitKey(1)

			# キーボードの「1」を押すと、距離指定に変更
			if key == ord(KEY_1):
				os.system('clear')
				print(DISTANCE_MODE_MSG)
				print(">距離指定に変更")
				direction = input("方向を入力してください\n")
				unit      = input("単位を入力してください\n")
				distance  = input("距離を入力してください\n")

				show = True

				# 期待されない入力は受け付けない(上に記載)
				if direction not in WASD or unit not in C_OR_M or not distance.isdecimal():
					print("入力が正しくありません")
					continue
				r.set('command', KEY_1 + " " + direction + " " + unit + " " + distance)
			
			# キーボードの「2」を押すと、角度指定に変更
			if key == ord(KEY_2):
				os.system('clear')
				print(ANGLE_MODE_MSG)
				print(">角度指定に変更")
				angle = input("角度を入力してください\n")

				show = True

				# 期待されない入力は受け付けない(上に記載)
				if not is_num(angle):
					print("入力が正しくありません")
					continue
				r.set('command', KEY_2 + " " + "None" + " " + "None" + " " + angle)
				
			# キーボードの「2」を押すと、上昇/下降距離指定に変更
			if key == ord(KEY_3):
				os.system('clear')
				print(VERTICAL_MODE_MSG)
				print(">上昇/下降距離指定に変更")
				direction = input("方向を入力してください\n")
				unit      = input("単位を入力してください\n")
				distance  = input("距離を入力してください\n")

				show = True

				# 期待されない入力は受け付けない(上に記載)
				if direction not in RF or unit not in C_OR_M or not distance.isdecimal():
					print("入力が正しくありません")
					continue
				r.set('command', KEY_3 + " " + direction + " " + unit + " " + distance)

			if key == ESC:				# reset
				r.set('command', '_reset')
				print("リセット")
				timer(15)
				show = True
			elif key == L_SHIFT or key == TAB:
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

			if(key == ord('p')):
				os.system('clear')
				print(MANUAL_MSG)
				show = True
			
			if(show == True):
				print("次の操作を待っています...")
				show = False

	except( KeyboardInterrupt, SystemExit):    # if Ctrl+c is pressed, quit program.
		print( "Detect SIGINT." )
