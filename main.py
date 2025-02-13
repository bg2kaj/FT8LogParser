import JLPEngine
import json
import configparser
import os
import sys
import time
import locale
import sqlite3
from tqdm import tqdm
from datetime import datetime, timedelta
import csv

#本地变量组
ver=2.1 #Version
sys_language=0 #0-any 1-chn
local_latitude=39.5
local_longitude=-115.70
log_file_type=1 #1-JTDX, 2-WSJT-X
parse_step=0
log_file_name=""
insert_data=()

def main():
    language = locale.getdefaultlocale()[0]
    global sys_language
    global log_file_name
    global log_file_type
    global local_latitude
    global local_longitude
    global parse_step
    try:
        os.remove("JLP.db")
    except:
        pass
    os.system('copy template.sys JLP.db')
    if(language.startswith('zh')):
        sys_language=1
        printTitle_cn()
    else:
        sys_language=0
        printTitle_en()
    config_file=configparser.ConfigParser()
    config_file.read("config.ini")
    local_latitude=config_file.getfloat('STATION','LATITUDE')
    local_longitude=config_file.getfloat('STATION','LONGITUDE')
    parse_step=config_file.getint('ANALYSE','ACCURACY')

    if(sys_language==1):
        print("本地经纬度为：",local_longitude,local_latitude)
    else:
        print("Station Longitude and latitude are：",local_longitude,local_latitude)
    sys_argv_tester()
    start_processing_timestamp=time.time()
    if(log_file_type==1):
        JTDX_File_parser(log_file_name,sys_language)
    else:
        WSJT_File_parser(log_file_name,sys_language)

    db_summary()
    stop_processing_timestamp=time.time()
    delta_time=stop_processing_timestamp-start_processing_timestamp

    print("分析已经完成！共消耗时间：",int(delta_time),"秒，现在开始导出。")
    output_filename=log_file_name.split(".")[0]
    SQLite_export(output_filename)
    os.remove("JLP.db")

def JTDX_File_parser(filename,language):
    file_length=0
    contact_id=0
    try:
        Lib_file=open("cty.json",'r')
        for line in Lib_file.readlines():
            json_data=json.loads(line)
    except:
        if(language==0):
            print("cty.json missing or corrupted. Run datparse.exe to generate a new one from cty.dat.")
        else:
            print("cty.json 文件未找到或已受损，运行datparse.exe来从cty.dat中重建一个json文件。")
        exit()
    try:
        log_file_handle=open(filename,"r")
        if(language==0):
            print("Log file opened.")
        else:
            print("打开日志文件成功，开始读取日志内容...")
        file_length = len(log_file_handle.readlines())
        log_file_handle.close()
        log_file_handle=open(filename,"r")
    except:
        if(language==0):
            print("Log file open failed, What's going on?")
            exit()
        else:
            print("文件打开失败！这怎么了？")
            exit()
    db_handler=sqlite3.connect("JLP.db")
    cur=db_handler.cursor()
    with tqdm(total=file_length) as pbar:
        pbar.unit="Lines "
        for log_raw_line in log_file_handle:
            try:
                line_process_result=JLPEngine.JLP_LogLinePreprocess(log_raw_line)
                if(line_process_result==-1):
                    line_process_result=JLPEngine.JLP_JTDXAuxiliaryParser(log_raw_line)
                    if(line_process_result==-1):
                        continue
                    else:
                        contact_band=line_process_result
                else:
                    if(str(line_process_result[8]).isalpha()==False)and(str(line_process_result[8]).isdigit()==False):
                        #一种特殊情况：如果指定呼叫，需检查呼号位是否全是数字（isdigit否）且包含数字和字符（isalpha否）
                        line_further_digest=JLPEngine.JLP_QueryCallsignInformation(line_process_result[8],json_data)
                        distance_calculated=JLPEngine.JLP_CalculateDistance(line_further_digest["lat"],line_further_digest["long"],local_latitude,local_longitude)
                        #Output
                        contact_id+=1
                        contact_distance=round(distance_calculated)
                        contact_snr=int(line_process_result[7])
                        contact_continent=line_further_digest["continent"]
                        contact_year=line_process_result[0]
                        contact_month=line_process_result[1]
                        contact_day=line_process_result[2]
                        contact_hour=line_process_result[3]
                        contact_minute=line_process_result[4]
                        contact_second=line_process_result[5]
                        contact_sql_timestamp=line_process_result[9]
                        insert_data=({"id":contact_id,"band":contact_band,"distance":contact_distance,"snr":contact_snr,"continent":contact_continent,"date":contact_sql_timestamp})
                        try:
                            cur.execute("INSERT INTO contacts VALUES(:id,:band,:distance,:snr,:continent,:date)",insert_data)
                        except Exception as e:
                            pass
            except Exception as f:
                pass
            pbar.update(1)
    print("文件处理结束，共有",contact_id,"条数据得到处理，部分元数据不包含有效信息，已省略。")
    db_handler.commit()
    db_handler.close()

def WSJT_File_parser(filename,language):
    contact_id=0
    try:
        Lib_file=open("cty.json",'r')
        for line in Lib_file.readlines():
            json_data=json.loads(line)
    except:
        if(language==0):
            print("cty.json missing or corrupted. Run datparse.exe to generate a new one from cty.dat.")
        else:
            print("cty.json 文件未找到或已受损，运行datparse.exe来从cty.dat中重建一个json文件。")
        exit()
    try:
        log_file_handle=open(filename,"r")
        if(language==0):
            print("Log file opened.")
        else:
            print("打开日志文件成功，开始读取日志内容...")
        file_length = len(log_file_handle.readlines())
        log_file_handle.close()
        log_file_handle=open(filename,"r")
    except:
        if(language==0):
            print("Log file open failed, What's going on?")
            exit()
        else:
            print("文件打开失败！这怎么了？")
            exit()
    db_handler=sqlite3.connect("JLP.db")
    cur=db_handler.cursor()
    with tqdm(total=file_length) as pbar:
        pbar.unit="Lines "
        for log_raw_line in log_file_handle:
            try:
                line_process_result=JLPEngine.JLP_LogLinePreprocess(log_raw_line)
                if(line_process_result==-1):
                    continue
                else:
                    if(str(line_process_result[8]).isalpha()==False)and(str(line_process_result[8]).isdigit()==False):
                        #一种特殊情况：如果指定呼叫，需检查呼号位是否全是数字（isdigit否）且包含数字和字符（isalpha否）
                        line_further_digest=JLPEngine.JLP_QueryCallsignInformation(line_process_result[8],json_data)
                        distance_calculated=JLPEngine.JLP_CalculateDistance(line_further_digest["lat"],line_further_digest["long"],local_latitude,local_longitude)
                        #output
                        contact_id+=1
                        contact_band=JLPEngine.JLP_FreqToBand(int(line_process_result[6]))
                        contact_distance=round(distance_calculated)
                        contact_snr=int(line_process_result[7])
                        contact_continent=line_further_digest["continent"]
                        contact_year=line_process_result[0]
                        contact_month=line_process_result[1]
                        contact_day=line_process_result[2]
                        contact_hour=line_process_result[3]
                        contact_minute=line_process_result[4]
                        contact_second=line_process_result[5]
                        contact_sql_timestamp=line_process_result[9]
                        insert_data=({"id":contact_id,"band":contact_band,"distance":contact_distance,"snr":contact_snr,"continent":contact_continent,"date":contact_sql_timestamp})
                        try:
                            cur.execute("INSERT INTO contacts VALUES(:id,:band,:distance,:snr,:continent,:date)",insert_data)
                        except Exception as e:
                            pass
            except:
                pass
            pbar.update(1)
    print("文件处理结束，共有",contact_id,"条数据得到处理，部分元数据不包含有效信息，已省略。") 
    db_handler.commit()
    db_handler.close()

def db_summary():
    #首先获取该日志中最小日期和最大日期
    # 从配置文件中获取遍历步长 - 在主函数里搞定了
    # 然后，开始遍历
    # 遍历时，首先查询当前步长内是否有记录，如果无记录，则继续
    # 如果有记录，计算所有参数
    global parse_step
    band_list=[160,80,60,40,30,20,17,15,12,10,6,2]

    db_handler=sqlite3.connect("JLP.db")
    cur=db_handler.cursor()
    query_min_max = "SELECT MIN(date) AS min_date, MAX(date) AS max_date FROM contacts;"
    cur.execute(query_min_max)
    result = cur.fetchone()
    min_date = result[0]
    max_date = result[1]
    print ("待分析的日志起始于：",min_date," 结束于：",max_date)
    #开始时间向前取整1天，结束时间向后取整1天
    #即开始时间 20240101 122334取整为20240101 000000
    #结束时间 20240202 122334取整为20240202 235959

    interval=timedelta(minutes=parse_step)
    current_start = datetime.strptime(min_date,'%Y%m%d %H%M%S')
    current_start=current_start.replace(hour=0,minute=0,second=0)
    max_date_end=datetime.strptime(max_date,'%Y%m%d %H%M%S')
    max_date_end=max_date_end.replace(hour=23,minute=59,second=59)
    total_records = 0
    
    print("开始分析具体数据，请不要退出程序，等待分析完成。中途退出将不会得到结果。")

    #进度条总体长度：分钟
    progressbar_total=int(int(max_date_end.timestamp()-current_start.timestamp())/60)+1
    #每次处理的进度：分钟
    progressbar_step=parse_step
    print("总时间跨度：",progressbar_total," 分钟，每次分析的时间粒度：",parse_step,"分钟。")
    pbar=tqdm(total=progressbar_total,unit="Minutes ")

    while current_start < max_date_end:
        current_end = current_start + interval
        if current_end > max_date_end:
            current_end = max_date_end


        #首先查询本时间段内是否有数据
        query = f"""
            SELECT COUNT(*)
            FROM contacts
            WHERE date >= '{datetime.strftime(current_start,'%Y%m%d %H%M%S')}'
            AND date < '{datetime.strftime(current_end,'%Y%m%d %H%M%S')}'
            """
        cur.execute(query)

        rows = cur.fetchall()
        step_item_count=rows[0][0]
        if(step_item_count==0):   #如果没有数据，直接下一循环
            pbar.update(progressbar_step)
            current_start = current_end
            continue
        else:
            # 处理数据
            # print ("\n在UTC",datetime.strftime(current_start,'%Y%m%d %H%M%S'),"与",datetime.strftime(current_end,'%Y%m%d %H%M%S'),"之间有",step_item_count,"条数据。")
            #分波段查询
            for band in band_list:
                # print ("在",band,"波段上：")
                #查询本时段内总计数和平均SNR
                query = f"""
                    SELECT COUNT(*) AS count, AVG(snr) AS average_snr
                    FROM contacts
                    WHERE date >= '{datetime.strftime(current_start,'%Y%m%d %H%M%S')}'
                    AND date < '{datetime.strftime(current_end,'%Y%m%d %H%M%S')}' AND band = '{band}'
                    """
                cur.execute(query)
                rows = cur.fetchall()
                if(rows[0][0]!=0):
                    # print("共有数量：",rows[0][0],"平均SNR为：",round(rows[0][1],1))
                    analyse_count=step_item_count
                    analyse_avg_snr=round(rows[0][0],1)
                else:
                    # print("共有数量：",rows[0][0])
                    continue
                    # print("共有数量：",rows[0][0])
                    # analyse_count=step_item_count
                    # analyse_avg_snr=0

                #查询本时段内各大洲的计数和平均SNR
                query = f"""
                    SELECT COUNT(*) AS count, AVG(snr) AS average_snr FROM contacts WHERE continent = 'AS' AND
                    date >= '{datetime.strftime(current_start,'%Y%m%d %H%M%S')}'
                    AND date < '{datetime.strftime(current_end,'%Y%m%d %H%M%S')}' AND band = '{band}'
                    """
                cur.execute(query)
                rows = cur.fetchall()
                if(rows[0][0]!=0):
                    # print("其中，亚洲数量：",rows[0][0],"，平均信噪比：",round(rows[0][1],1))   
                    analyse_as_count=rows[0][0]
                    analyse_as_avg_snr=round(rows[0][1],1)
                else:
                    # print("其中，亚洲数量：",rows[0][0])  
                    analyse_as_count=rows[0][0]
                    analyse_as_avg_snr=0

                query = f"""
                    SELECT COUNT(*) AS count, AVG(snr) AS average_snr FROM contacts WHERE continent = 'EU' AND
                    date >= '{datetime.strftime(current_start,'%Y%m%d %H%M%S')}'
                    AND date < '{datetime.strftime(current_end,'%Y%m%d %H%M%S')}' AND band = '{band}'
                    """
                cur.execute(query)
                rows = cur.fetchall()
                if(rows[0][0]!=0):
                    # print("欧洲数量：",rows[0][0],"，平均信噪比：",round(rows[0][1],1))   
                    analyse_eu_count=rows[0][0]
                    analyse_eu_avg_snr=round(rows[0][1],1)
                else:
                    # print("欧洲数量：",rows[0][0])  
                    analyse_eu_count=rows[0][0]
                    analyse_eu_avg_snr=0

                query = f"""
                    SELECT COUNT(*) AS count, AVG(snr) AS average_snr FROM contacts WHERE continent = 'NA' AND
                    date >= '{datetime.strftime(current_start,'%Y%m%d %H%M%S')}'
                    AND date < '{datetime.strftime(current_end,'%Y%m%d %H%M%S')}' AND band = '{band}'
                    """
                cur.execute(query)
                rows = cur.fetchall()
                if(rows[0][0]!=0):
                    # print("北美数量：",rows[0][0],"，平均信噪比：",round(rows[0][1],1))   
                    analyse_na_count=rows[0][0]
                    analyse_na_avg_snr=round(rows[0][1],1)
                else:
                    # print("北美数量：",rows[0][0])  
                    analyse_na_count=rows[0][0]
                    analyse_na_avg_snr=0

                query = f"""
                    SELECT COUNT(*) AS count, AVG(snr) AS average_snr FROM contacts WHERE continent = 'SA' AND
                    date >= '{datetime.strftime(current_start,'%Y%m%d %H%M%S')}'
                    AND date < '{datetime.strftime(current_end,'%Y%m%d %H%M%S')}' AND band = '{band}'
                    """
                cur.execute(query)
                rows = cur.fetchall()
                if(rows[0][0]!=0):
                    # print("南美数量：",rows[0][0],"，平均信噪比：",round(rows[0][1],1))   
                    analyse_sa_count=rows[0][0]
                    analyse_sa_avg_snr=round(rows[0][1],1)
                else:
                    # print("南美数量：",rows[0][0])  
                    analyse_sa_count=rows[0][0]
                    analyse_sa_avg_snr=0

                query = f"""
                    SELECT COUNT(*) AS count, AVG(snr) AS average_snr FROM contacts WHERE continent = 'AF' AND
                    date >= '{datetime.strftime(current_start,'%Y%m%d %H%M%S')}'
                    AND date < '{datetime.strftime(current_end,'%Y%m%d %H%M%S')}' AND band = '{band}'
                    """
                cur.execute(query)
                rows = cur.fetchall()
                if(rows[0][0]!=0):
                    # print("非洲数量：",rows[0][0],"，平均信噪比：",round(rows[0][1],1))   
                    analyse_af_count=rows[0][0]
                    analyse_af_avg_snr=round(rows[0][1],1)
                else:
                    # print("非洲数量：",rows[0][0])  
                    analyse_af_count=rows[0][0]
                    analyse_af_avg_snr=0

                query = f"""
                    SELECT COUNT(*) AS count, AVG(snr) AS average_snr FROM contacts WHERE continent = 'OC' AND
                    date >= '{datetime.strftime(current_start,'%Y%m%d %H%M%S')}'
                    AND date < '{datetime.strftime(current_end,'%Y%m%d %H%M%S')}' AND band = '{band}'
                    """
                cur.execute(query)
                rows = cur.fetchall()
                if(rows[0][0]!=0):
                    # print("大洋洲数量：",rows[0][0],"，平均信噪比：",round(rows[0][1],1))   
                    analyse_oc_count=rows[0][0]
                    analyse_oc_avg_snr=round(rows[0][1],1)
                else:
                    # print("大洋数量：",rows[0][0])  
                    analyse_oc_count=rows[0][0]
                    analyse_oc_avg_snr=0
                #似乎bigcty不会抛出其他大洲,无视但保留这项保证数据库正确
                analyse_otr_count=0
                analyse_otr_avg_snr=0

                #查询本时段内各距离的计数和平均SNR
                query = f"""
                    SELECT COUNT(*) AS count, AVG(snr) AS average_snr FROM contacts WHERE distance<1000 AND
                    date >= '{datetime.strftime(current_start,'%Y%m%d %H%M%S')}'
                    AND date < '{datetime.strftime(current_end,'%Y%m%d %H%M%S')}' AND band = '{band}'
                    """
                cur.execute(query)
                rows = cur.fetchall()
                if(rows[0][0]!=0):
                    # print("距离 <1000 数量：",rows[0][0],"，平均信噪比：",round(rows[0][1],1))
                    analyse_dis_l1k_count=rows[0][0]
                    analyse_dis_l1k_avg_snr=round(rows[0][1],1)
                else:
                    # print("距离 <1000 数量：",rows[0][0],)
                    analyse_dis_l1k_count=rows[0][0]
                    analyse_dis_l1k_avg_snr=0

                query = f"""
                    SELECT COUNT(*) AS count, AVG(snr) AS average_snr FROM contacts WHERE distance>1000 AND distance<=3000 AND
                    date >= '{datetime.strftime(current_start,'%Y%m%d %H%M%S')}'
                    AND date < '{datetime.strftime(current_end,'%Y%m%d %H%M%S')}' AND band = '{band}'
                    """
                cur.execute(query)
                rows = cur.fetchall()
                if(rows[0][0]!=0):
                    # print("距离 1000<x<=3000 数量：",rows[0][0],"，平均信噪比：",round(rows[0][1],1))
                    analyse_dis_1k3k_count=rows[0][0]
                    analyse_dis_1k3k_avg_snr=round(rows[0][1],1)
                else:
                    # print("距离 1000<x<=3000 数量：",rows[0][0],)
                    analyse_dis_1k3k_count=rows[0][0]
                    analyse_dis_1k3k_avg_snr=0

                query = f"""
                    SELECT COUNT(*) AS count, AVG(snr) AS average_snr FROM contacts WHERE distance>3000 AND distance<=5000 AND
                    date >= '{datetime.strftime(current_start,'%Y%m%d %H%M%S')}'
                    AND date < '{datetime.strftime(current_end,'%Y%m%d %H%M%S')}' AND band = '{band}'
                    """
                cur.execute(query)
                rows = cur.fetchall()
                if(rows[0][0]!=0):
                    # print("距离 3000<x<=5000 数量：",rows[0][0],"，平均信噪比：",round(rows[0][1],1))
                    analyse_dis_3k5k_count=rows[0][0]
                    analyse_dis_3k5k_avg_snr=round(rows[0][1],1)
                else:
                    # print("距离 3000<x<=5000 数量：",rows[0][0],)
                    analyse_dis_3k5k_count=rows[0][0]
                    analyse_dis_3k5k_avg_snr=0

                query = f"""
                    SELECT COUNT(*) AS count, AVG(snr) AS average_snr FROM contacts WHERE distance>5000 AND distance<=7000 AND
                    date >= '{datetime.strftime(current_start,'%Y%m%d %H%M%S')}'
                    AND date < '{datetime.strftime(current_end,'%Y%m%d %H%M%S')}' AND band = '{band}'
                    """
                cur.execute(query)
                rows = cur.fetchall()
                if(rows[0][0]!=0):
                    # print("距离 5000<x<=7000 数量：",rows[0][0],"，平均信噪比：",round(rows[0][1],1))
                    analyse_dis_5k7k_count=rows[0][0]
                    analyse_dis_5k7k_avg_snr=round(rows[0][1],1)
                else:
                    # print("距离 5000<x<=7000 数量：",rows[0][0],)
                    analyse_dis_5k7k_count=rows[0][0]
                    analyse_dis_5k7k_avg_snr=0

                query = f"""
                    SELECT COUNT(*) AS count, AVG(snr) AS average_snr FROM contacts WHERE distance>7000 AND distance<=9000 AND
                    date >= '{datetime.strftime(current_start,'%Y%m%d %H%M%S')}'
                    AND date < '{datetime.strftime(current_end,'%Y%m%d %H%M%S')}' AND band = '{band}'
                    """
                cur.execute(query)
                rows = cur.fetchall()
                if(rows[0][0]!=0):
                    # print("距离 7000<x<=9000 数量：",rows[0][0],"，平均信噪比：",round(rows[0][1],1))
                    analyse_dis_7k9k_count=rows[0][0]
                    analyse_dis_7k9k_avg_snr=round(rows[0][1],1)
                else:
                    # print("距离 7000<x<=9000 数量：",rows[0][0],)
                    analyse_dis_7k9k_count=rows[0][0]
                    analyse_dis_7k9k_avg_snr=0

                query = f"""
                    SELECT COUNT(*) AS count, AVG(snr) AS average_snr FROM contacts WHERE distance>9000 AND distance<=11000 AND
                    date >= '{datetime.strftime(current_start,'%Y%m%d %H%M%S')}'
                    AND date < '{datetime.strftime(current_end,'%Y%m%d %H%M%S')}' AND band = '{band}'
                    """
                cur.execute(query)
                rows = cur.fetchall()
                if(rows[0][0]!=0):
                    # print("距离 9000<x<=11000 数量：",rows[0][0],"，平均信噪比：",round(rows[0][1],1))
                    analyse_dis_9k11k_count=rows[0][0]
                    analyse_dis_9k11k_avg_snr=round(rows[0][1],1)
                else:
                    # print("距离 9000<x<=11000 数量：",rows[0][0],)
                    analyse_dis_9k11k_count=rows[0][0]
                    analyse_dis_9k11k_avg_snr=0

                query = f"""
                    SELECT COUNT(*) AS count, AVG(snr) AS average_snr FROM contacts WHERE distance>11000 AND
                    date >= '{datetime.strftime(current_start,'%Y%m%d %H%M%S')}'
                    AND date < '{datetime.strftime(current_end,'%Y%m%d %H%M%S')}' AND band = '{band}'
                    """
                cur.execute(query)
                rows = cur.fetchall()
                if(rows[0][0]!=0):
                    # print("距离 >11000 数量：",rows[0][0],"，平均信噪比：",round(rows[0][1],1))
                    analyse_dis_o11k_count=rows[0][0]
                    analyse_dis_o11k_avg_snr=round(rows[0][1],1)
                else:
                    # print("距离 >11000 数量：",rows[0][0],)
                    analyse_dis_o11k_count=rows[0][0]
                    analyse_dis_o11k_avg_snr=0
                #写入本时间段本波段的数据
                analyse_year=current_start.year
                analyse_month=current_start.month
                analyse_day=current_start.day
                analyse_hour=current_start.hour
                analyse_minute=current_start.minute
                analyse_band=band
                analyse_SQL_date=datetime.strftime(current_start,'%Y%m%d %H%M%S')
                insert_data=({"year":analyse_year,"month":analyse_month,"day":analyse_day,"hour":analyse_hour,"minute":analyse_minute,"band":analyse_band,"count":analyse_count,"avg_snr":analyse_avg_snr,"as_count":analyse_as_count,"as_avg_snr":analyse_as_avg_snr,"eu_count":analyse_eu_count,"eu_avg_snr":analyse_eu_avg_snr,"na_count":analyse_na_count,"na_avg_snr":analyse_na_avg_snr,"sa_count":analyse_sa_count,"sa_avg_snr":analyse_sa_avg_snr,"af_count":analyse_af_count,"af_avg_snr":analyse_af_avg_snr,"oc_count":analyse_oc_count,"oc_avg_snr":analyse_oc_avg_snr,"otr_count":analyse_otr_count,"otr_avg_snr":analyse_otr_avg_snr,"dis_l1k_count":analyse_dis_l1k_count,"dis_l1k_avg_snr":analyse_dis_l1k_avg_snr,"dis_1k3k_count":analyse_dis_1k3k_count,"dis_1k3k_avg_snr":analyse_dis_1k3k_avg_snr,"dis_3k5k_count":analyse_dis_3k5k_count,"dis_3k5k_avg_snr":analyse_dis_3k5k_avg_snr,"dis_5k7k_count":analyse_dis_5k7k_count,"dis_5k7k_avg_snr":analyse_dis_5k7k_avg_snr,"dis_7k9k_count":analyse_dis_7k9k_count,"dis_7k9k_avg_snr":analyse_dis_7k9k_count,"dis_9k11k_count":analyse_dis_9k11k_count,"dis_9k11k_avg_snr":analyse_dis_9k11k_avg_snr,"dis_o11k_count":analyse_dis_o11k_count,"dis_o11k_avg_snr":analyse_dis_o11k_avg_snr,"date":analyse_SQL_date})
                try:
                    cur.execute("INSERT INTO analyse VALUES(:year, :month, :day, :hour, :minute, :band, :count, :avg_snr, :as_count, :as_avg_snr, :eu_count, :eu_avg_snr, :na_count, :na_avg_snr, :sa_count, :sa_avg_snr, :af_count, :af_avg_snr, :oc_count, :oc_avg_snr, :otr_count, :otr_avg_snr, :dis_l1k_count, :dis_l1k_avg_snr, :dis_1k3k_count, :dis_1k3k_avg_snr, :dis_3k5k_count, :dis_3k5k_avg_snr, :dis_5k7k_count, :dis_5k7k_avg_snr, :dis_7k9k_count, :dis_7k9k_avg_snr, :dis_9k11k_count, :dis_9k11k_avg_snr, :dis_o11k_count, :dis_o11k_avg_snr, :date)",insert_data)
                except Exception as e:
                    # print(e)
                    pass

            #处理循环结构
            current_start = current_end
            step_item_count=0
            pbar.update(progressbar_step)
    #进度条
    
    
    db_handler.commit()
    db_handler.close()
    return(1)
        
def SQLite_export(output_filename):
    db_handler=sqlite3.connect("JLP.db")
    cur=db_handler.cursor()
    cur.execute("SELECT * from analyse")
    output_name="analyse_result_"+output_filename+".csv"
    with open(output_name, "w",newline='') as csv_file:
        csv_writer = csv.writer(csv_file, delimiter=",")
        csv_writer.writerow([i[0] for i in cur.description])
        csv_writer.writerows(cur)
    print("分析完的统计数据已经被保存至",output_name,"中，你可以用Excel打开，并提取自己感兴趣的部分进行进一步分析。")
    db_handler.close()

def sys_argv_tester():
    global log_file_type
    global log_file_name
    now_band=0
    if((len(sys.argv)==1)or(len(sys.argv)>3)):
        printUsage(sys_language)
        sys.exit()
    else:
        if(sys_language==0):
            if(sys.argv[1]=='-j'):
                print("Read a JTDX log file, file name is "+sys.argv[2])
                log_file_type=1
            else:
                if(sys.argv[1]=='-t'):
                    print("Read a WSJT-X log file, file name is "+sys.argv[2])
                    log_file_type=2
                else:
                    print("Invalid log file type.")
                    printUsage(sys_language)
                    sys.exit()
        else:
            if(sys.argv[1]=='-j'):
                print("指定了JTDX日志文件, 文件名为 "+sys.argv[2])
                log_file_type=1
            else:
                if(sys.argv[1]=='-t'):
                    print("指定了WSJT-X日志文件, 文件名为"+sys.argv[2])
                    log_file_type=2
                else:
                    print("非法的文件类型。")
                    printUsage(sys_language)
                    sys.exit()
        log_file_name=sys.argv[2]

def printUsage(language):
    if(language==0):
        print ("Incorrect command line argument!")
        print ("Usage: ")
        print ("FT8LogParser.exe -x y.txt")
        print ("-x could be -j or -t, -j indicate log file is generated by JTDX and -t indicate log file is generated by WSJT-X.")
        print ("y.txt is the log file, the original name maybe 202401_ALL.txt (JTDX) or ALL.txt (WSJT-X).")
        print ("Input proper command and try again!")
        print ("")
    else:
        print ("输入的命令行参数不正确！")
        print ("程序用法: ")
        print ("FT8LogParser.exe -x y.txt")
        print ("-x 可以是 -j or -t, -j 提示程序解析JTDX产生的日志文件， -t 提示程序解析WSJT-X产生的日志文件。")
        print ("y.txt 是日志文件名, 它可能是202401_ALL.txt (JTDX) 或者 ALL.txt (WSJT-X)。")
        print ("请输入正确的命令行参数，然后再试一次。")
        print ("")

def printTitle_en():
    os.system('cls')
    print (" ")    
    print ("  ______  _______  ___   _                    _____                              ")
    print (" |  ____||__   __|/ _ \ | |                  |  __ \                             ")
    print (" | |__      | |  | (_) || |      ___    __ _ | |__) |__ _  _ __  ___   ___  _ __ ")
    print (" |  __|     | |   > _ < | |     / _ \  / _` ||  ___// _` || '__|/ __| / _ \| '__|")
    print (" | |        | |  | (_) || |____| (_) || (_| || |   | (_| || |   \__ \|  __/| |   ")
    print (" |_|        |_|   \___/ |______|\___/  \__, ||_|    \__,_||_|   |___/ \___||_|   ")
    print ("                                        __/ |                                    ")
    print ("                                       |___/                                     "+"  Ver. "+str(ver))
    print ("")
    print ("======================================================================================================")
    print ("A simple JTDX/WSJT-X decoded log file analysis and summary generator.")
    print ("\'JLP stands for JTDX Log Parser, but now should work along with WSJT-X log files.\n So why not name it FT8LogParser.\'")
    print ("                                                            -- Written by BG2KAJ.")
    print ("")
    print ("This program is written purely for personal need and shared to hope it could be ")
    print ("useful. The program shall not be used in any subjects other than ham radio and  ")
    print ("no guarantee for it's result's correctness. Author of it could not give any kind")
    print ("of support of the program/result since it's only a hobby product. You've be warn")
    print ("ed about that!                                                                  ")
    print ("")

def printTitle_cn():
    os.system('cls')
    print (" ")    
    print ("  ______  _______  ___   _                    _____                              ")
    print (" |  ____||__   __|/ _ \ | |                  |  __ \                             ")
    print (" | |__      | |  | (_) || |      ___    __ _ | |__) |__ _  _ __  ___   ___  _ __ ")
    print (" |  __|     | |   > _ < | |     / _ \  / _` ||  ___// _` || '__|/ __| / _ \| '__|")
    print (" | |        | |  | (_) || |____| (_) || (_| || |   | (_| || |   \__ \|  __/| |   ")
    print (" |_|        |_|   \___/ |______|\___/  \__, ||_|    \__,_||_|   |___/ \___||_|   ")
    print ("                                        __/ |                                    ")
    print ("                                       |___/                                     "+"  Ver. "+str(ver))
    print ("")
    print ("======================================================================================================")
    print ("解析JTDX/WSJT-X解码日志文件并分析、给出总结报告的简单程序")
    print ("\'JLP 代表 JTDX Log Parser, 但现在应该也能解析 WSJT-X 的日志文件。不如改名FT8LogParser.\'")
    print ("                                                                        ——作者 BG2KAJ.")
    print ("")
    print ("此程序完全是出于个人需要而编写的，谨希望分享该软件能够为其他爱好者提供帮助。该程序不应该")
    print ("被使用在与业余无线电所不相关的领域内。对于程序给出的计算结果的正确性不做保证。由于其仅为")
    print ("爱好之作，作者无法对软件本身及其计算结果提供技术支持。敬请了解。")
    print ("")

if(__name__=='__main__'):
    main()   