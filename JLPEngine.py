import json
from math import sin, cos, sqrt, atan2, radians

R = 6373.0

def JLP_LogLinePreprocess(line,softtype_default=7):
    #获取输入有效日志条目的信息
    #输入值：单条日志文件,软件类型：1=JTDX 2=WSJT-X，不指定则有本函数自动识别，不过强烈建议传入一个参数！
    #输出值：返回list [年（4位），月（2位），日（2位），时（UTC2位）,分（2位），秒（2位），频率（如果是JTDX，此项为空），信噪比（负数），发送者呼号（字符串），SQL日期时间字符串]
    #首先处理输入，确定其为哪种软件的输出
    #JTDX的日志文件以~分割FT8信息，WSJT-X的日志文件以FT8分割模式
    #JTDX：20240220_021715  -6  1.7 1772 ~ CB0ZEW JR3XUH PM74        ^
    #WSJT-X：220812_141352   144.440 Rx FT8  -5  1.7 1610 JH2CDC LW3MOZ/R PN73
    #两种信息中，第一部分均为日期信息

    return_list=[]

    #首先判断软件种类
    if(softtype_default==7):
        if '~' in line:
            softtype=1
        elif ('Tx' in line) or ('Rx' in line):
            softtype=2
        else: 
            softtype=0
            return (-1)
    else:
        softtype=softtype_default
    
    #系统指定了一种软件格式，但是这种格式不符合解码规定（比如JTDX的指示性文字）
    if(((softtype==1)and(not('~' in line)))or(softtype==2)and(not(('Tx' in line) or ('Rx' in line)))):
        return -1

    #然后，整理日期时间
    datetime_line=line.split(' ')[0]
    datepart=datetime_line.split('_')[0]
    timepart=datetime_line.split('_')[1]
    if softtype == 1:
        year=int(datepart[0:4])
        month=int(datepart[4:6])
        day=int(datepart[6:8])
    elif softtype==2:
        year=int(datepart[0:2])+2000
        month=int(datepart[2:4])
        day=int(datepart[4:6])
    hour=int(timepart[0:2])
    minute=int(timepart[2:4])
    second=int(timepart[4:6])
    if softtype == 1:
        SQL_date_string=datepart+" "+timepart
    elif softtype==2:
        SQL_date_string="20"+datepart+" "+timepart
    #最后，获取对方频率，信噪比，呼号
    #一种特殊情况：如果指定呼叫，需检查呼号位是否全是数字（isdigit否）且包含数字和字符（isalpha否）
    if softtype==1:
        call_line=line.split('~')[1]
        callsign=call_line.split(' ')[2]
        snr_line=line.split('~')[0]
        snr=int(snr_line.split()[1])
        freq=0
    elif softtype==2 and (not('verified' in line)) and (not('Tx' in line)):
        call_line=line.split('FT8')[1]
        callsign=call_line.split()[-2]
        if not('FT8_SH' in line):
            freq=float((line.split('FT8')[0]).split()[1])
            snr=int((line.split('FT8')[1]).split()[0])
        else:
            freq=float((line.split('FT8_SH')[0]).split()[1])
            snr=int((line.split('FT8_SH')[1]).split()[0])
    elif softtype==2 and ('verified' in line):
        return -1
    elif softtype==2 and ('Tx' in line):#排除WSJT-X日志文件中因为记录了自己发射的语句而导致计算错误的问题
        return -1

    #为结构体赋值
    return_list.append(year)
    return_list.append(month)
    return_list.append(day)
    return_list.append(hour)
    return_list.append(minute)
    return_list.append(second)
    return_list.append(freq)
    return_list.append(snr)
    return_list.append(callsign)
    return_list.append(SQL_date_string)
    #返回值
    return return_list

def JLP_NetLinePreprocess(line):
    #从网络发来的实时解码信息中提取发送者呼号
    #输入值：信息内容字符串
    #输出值：对方呼号
    return_list=[]
    if(len(line.split(' '))==3)or(len(line.split(' '))==2):
        callsign=line.split(' ')[1]
        return callsign
    else:
        return -1

def JLP_QueryCallsignInformation(callsign,json_lib):
    #通过呼号和bigcty库查询对方呼号详细信息
    #输入值：对方呼号
    #返回值：详细信息
	callsign_length=len(callsign)
	looper=callsign_length
	query_success=0
	while(looper>0):
		callsign_tester=callsign[0:looper]
		looper-=1
		try:
			sub_data_call=json.dumps(json_lib[callsign_tester])
			sub_data_parsed_call=json.loads(sub_data_call)
		except:
			if(looper>0):
				continue
			else:
				query_success=0
				break
		else:
			query_success=1
			break

	if(query_success==1):
		return sub_data_parsed_call
	else:
		return -1

def JLP_CalculateDistance(dx_latitude,dx_longitude,local_latitude,local_longitude):
    #计算给定经纬度之间的距离
    #输入：dx_latitude：DX纬度,dx_longitude：DX经度,local_latitude：本地纬度,local_longitude：本地经度
    #输出：两点间距离，单位为km
	local_lat_ra=radians(local_latitude)
	local_long_ra=radians(local_longitude)
	dx_lat_ra=radians(dx_latitude)
	dx_long_ra=radians(dx_longitude)

	dlong=dx_long_ra-local_long_ra
	dlat=dx_lat_ra-local_lat_ra
	a = sin(dlat / 2)**2 + cos(dx_lat_ra) * cos(local_lat_ra) * sin(dlong / 2)**2
	c = 2 * atan2(sqrt(a), sqrt(1 - a))
	distance=R*c
	return distance


def JLP_FreqToBand(freq_str):
	try:
		freq_parsed=float(freq_str)
		if(freq_parsed<2):
			now_band=160  #160
		elif(freq_parsed>=3.5)and(freq_parsed<4):
			now_band=80  #80
		elif(freq_parsed>=5)and(freq_parsed<5.5):
			now_band=60  #60
		elif(freq_parsed>=7)and(freq_parsed<7.3):
			now_band=40  #40
		elif(freq_parsed>=10.1)and(freq_parsed<10.15):
			now_band=30  #30
		elif(freq_parsed>=14)and(freq_parsed<14.4):
			now_band=20  #20
		elif(freq_parsed>=18)and(freq_parsed<18.2):
			now_band=17  #17
		elif(freq_parsed>=21)and(freq_parsed<21.5):
			now_band=15  #15
		elif(freq_parsed>=24.8)and(freq_parsed<24.99):
			now_band=12  #12
		elif(freq_parsed>=28)and(freq_parsed<30):
			now_band=10 #10
		elif(freq_parsed>=50)and(freq_parsed<54):
			now_band=6 #6
		elif(freq_parsed>=144)and(freq_parsed<148):
			now_band=2 #6
		else:
			now_band=-2 #unknown

	except:
		print("Band parse failed.")
	else:
		return now_band

def JLP_JTDXAuxiliaryParser(line):
    #解析JTDX日志文件中的指示性命令
    #输入：日志
    #输出：-1代表本行无意义，-2代表波段超出记录范围。160~6代表波段名称，
    #主要的几种命令
    # 20250101_080437  21.074 MHz  FT8 JTDX v2.2.0-rc155d382c2              指示了波段
    # 20250101_080444  21.074 MHz  FT8                                      指示了波段
    # 20250101_080430  partial loss of data                     d           可以忽略
    # 20250101_080605.474(0)  Transmitting 21.079 MHz  T10:  CQ BG2KAJ PN23 可以忽略
    # 20250107_040145.067(0)  QSO logged: BY6SX                             可以忽略  
    if('partial' in line):
        return -1
    elif('Transmitting' in line):
        return -1
    elif('logged' in line):
        return -1
    elif(line.split()[2]=='MHz'):
        return (JLP_FreqToBand(line.split()[1]))
    else:
        return -1
    