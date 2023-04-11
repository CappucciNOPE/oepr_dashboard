import dash
from dash import Dash, html, dcc, Input, Output, callback
import dash_auth
import pandas as pd
import plotly.express as px
import json
import os,sys
from urllib.request import urlopen
import signal
from datetime import date
import plotly.graph_objects as go
import kaleido
import plotly.io as pio
from fpdf import FPDF
from PIL import Image

VALID_USERNAME_PASSWORD_PAIRS = {
    'emergencyprep':'tulane1555'
}
#external_stylesheets=['/Users/mmontgomery/Documents/Spring 2023/OEPR/readiness_dashboard/assets/format.css']#<-- not working, but fuck the front end anyway

#data = pd.read_csv("/Users/temp/Documents/readiness_dashboard/temporary2.csv")#Local
data = pd.read_csv("https://raw.githubusercontent.com/CappucciNOPE/oepr_dashboard/main/temporary2.csv")#deployed
cols = data.columns
train_types = list(pd.unique(data.loc[data['Event_Type']!="Monitoring"]['Event']))
orgs=list(pd.unique(data['Department/Organization']))
data['Start_Date/Time'] = pd.to_datetime(data['Start_Date/Time'])
data['End_Date/Time'] = pd.to_datetime(data['End_Date/Time'])
data['Date'] = pd.to_datetime(data['Date'])
"""dates = []
for event in data['Start_Date/Time']:
    if len(str(event.month))==1:
        month = '0'+str(event.month)
    else:
        month = str(event.month)
    if len(str(event.day))==1:
        day = '0'+str(event.day) 
    else:
        day = str(event.day)
    dates.append(pd.to_datetime(event.fromisoformat(str(event.year)+'-'+month+'-'+day)))"""
#data['Date']=pd.to_datetime(dates)
#data.to_csv('/Users/mmontgomery/Documents/Spring 2023/OEPR/readiness_dashboard/temporary2.csv')

#dash.register_page(__name__)
app = Dash(__name__)
server=app.server
auth = dash_auth.BasicAuth(
    app,
    VALID_USERNAME_PASSWORD_PAIRS
)
#layout = html.Div(
app.layout = html.Div([

    html.H1("Trainings"),
    html.Div([
        dcc.DatePickerRange(min_date_allowed=date(2022,1,1),max_date_allowed=date(2023,12,31), start_date=date(2023,1,1),end_date=date(2023,3,31),id='dates'),
        dcc.RadioItems(['Events','Attendance'],'Attendance',id='style'),
        dcc.Dropdown(orgs+['All'],'All',id='org',multi=True),
        html.Button(id="download",children='download'),
        dcc.Download(id="download-dataframe-csv"),
        dcc.RadioItems(["Print to PDF", "Display Only"],"Display Only",id='print')
    ]),
    html.Div([
        html.H3('Outreach'),
        dcc.Graph(id='bar',figure={}),
        dcc.Graph(id='timeline',figure={}),
        html.H3('Event Monitoring'),
        dcc.Graph(id='gantt',figure={}),
        ]
        )   
    ])
@app.callback(
    Output("download-dataframe-csv","data"),
    Input('download','n_clicks'),
    Input('dates','start_date'),
    Input('dates','end_date'),
    prevent_initial_call=True,
)

def download(n_clicks,start,end):
    return dcc.send_data_frame(data.to_csv, str(start)+"->"+str(end)+".csv")

@app.callback(
    Output('bar','figure'),
    Output('timeline','figure'),
    Output('gantt','figure'),
    Input('org','value'),
    Input('style','value'),
    Input('dates','start_date'),
    Input('dates','end_date'),
    Input("print",'value')
    )

def update_events(organizations,style,start_date, end_date, print):
    def vc(dfs):
        d = {}
        ds = []
        es = []
        cs = []
        dopts=pd.unique(dfs['Department/Organization'])
        eopts=pd.unique(dfs['Event'])
        for dopt in dopts:
            a = dfs.loc[dfs['Department/Organization']==dopt]
            for eopt in eopts:
                b = a.loc[a['Event']==eopt]
                l = len(b)
                ds.append(dopt)
                es.append(eopt)
                cs.append(l)
        d['Department/Organization']= ds
        d['Event']=es
        d['counts']=cs
        ret= pd.DataFrame.from_dict(d)
        ret.columns=['Department/Organization','Event','counts']
        return ret
    #filtering by dates:
    d = data.copy()
    start = pd.to_datetime(start_date)
    end = pd.to_datetime(end_date)
    d = d.loc[d['Date'] >= start]
    d = d.loc[d['Date'] < end]
    #d = d.loc[d['Date'] <= end]
    trainings = d.loc[d['Event_Type']=='Outreach']
    monitoring = d.loc[d['Event_Type']=='Monitoring']
    monitoring_events = monitoring.loc[monitoring['Event_Code']=='ME']
    monitoring_status = monitoring.loc[monitoring['Event_Code']=='MS']
    incidents = pd.DataFrame(d.loc[d['Event_Type']=='Incident'])
    i_comm = pd.DataFrame(incidents.loc[incidents['Event_Code']=='IC'])
    i_ncomm = pd.DataFrame(incidents.loc[incidents['Event_Code']=='IN'])
    events = monitoring.loc[monitoring["Event_Code"]=="EV"]
    #by organization
    if organizations != 'All' and 'All' not in organizations:
        """if str(type(organizations)) != 'class <list>':
            organizations = [organizations]"""
        print('selected',organizations)
        trainings=trainings.loc[trainings['Department/Organization'].isin(organizations)]

    #bar graph -- events
    #bar_data_evs = pd.DataFrame(trainings.groupby(by=['Department/Organization'],as_index=False)['Event'].value_counts())#,columns=['Department/Organization','Training_Type','Counts'])
    bar_data_evs = vc(trainings)
    bar_g_evs = px.bar(bar_data_evs,x='Department/Organization',y='counts',color='Event')
    bar_g_evs.update_layout(legend=dict(
    orientation="h",
    yanchor="bottom",
    y=1.02,
    xanchor="right",
    x=1
    ))
    #bar graph -- attendance
    bar_data_att = pd.DataFrame(trainings.groupby(by=['Department/Organization','Event'],as_index=False)['Attendance'].sum())#,columns=['Department/Organization','Training_Type','Counts'])
    bar_g_att = px.bar(bar_data_att,x='Department/Organization',y='Attendance',color='Event')
    bar_g_att.update_layout(legend=dict(
    orientation="h",
    yanchor="bottom",
    y=1.02,
    xanchor="right",
    x=1))
    
    if style == 'Events':
        bar_g = bar_g_evs
    elif style == 'Attendance':
        bar_g = bar_g_att
    #Scatter for outreach
    scatter = px.scatter(trainings,x='Start_Date/Time',y='Department/Organization',text='Attendance',color='Event',size='Attendance')
    scatter.update_traces(textposition='middle right')
    scatter.update_layout(xaxis_range=[start_date,end_date],width=1200, height=400)
    scatter.update_layout(legend=dict(
    orientation="h",
    yanchor="bottom",
    y=1.02,
    xanchor="right",
    x=1))
    
    #monitoring_graph = px.bar(monitoring,x=list(range(0,len(monitoring))),y='Department/Organization',color='Department/Organization')
    
    # monitoring events graph
    if len(events) > 0 :
        events_graph = px.timeline(events, x_start='Start_Date/Time',x_end='End_Date/Time',y='Department/Organization',text='Event')
        events_graph.update_traces()
        events_graph.update_layout(legend=dict(
        orientation="h",
        yanchor="bottom",
        y=1.02,
        xanchor="right",
        x=1))
    # monitoring timeline graph
    if len(monitoring_status) > 0:
        monitoring_graph = px.timeline(monitoring_status,x_start='Start_Date/Time',x_end='End_Date/Time',y='Event',color='Event',text='Event')
        monitoring_graph.update_layout(xaxis_range=[start_date,end_date],width=1600, height=400)
        monitoring_graph.update_traces()
        events_graph.add_traces(monitoring_graph.data)
    # monitoring status event
    if len(monitoring_events) > 0:
        monitoring_events_time = px.scatter(x=monitoring_events['Start_Date/Time'],y=monitoring_events['Department/Organization'],text=monitoring_events['Event'])
        monitoring_events_time.update_traces(marker_size=10,textposition='top center')
        events_graph.add_traces(monitoring_events_time.data)   
    # scatters for everbridge, for monitoring events, and for incidents  
    if len(i_comm) > 0:
        ever_graph = px.scatter(x = i_comm['Start_Date/Time'],y = i_comm['Department/Organization'],text=i_comm['Event'])
        ever_graph.update_traces(marker_size=10,textposition='top center')
        events_graph.add_traces(ever_graph.data)

    if len(i_ncomm) > 0:
        incident_p = px.scatter(x=i_ncomm['Start_Date/Time'],y=i_ncomm['Department/Organization'],text=i_ncomm['Event'])
        incident_p.update_traces(marker_size=10,textposition='top center')
        events_graph.add_traces(incident_p.data)
    
    if print == "Print to PDF":
        make_pdf(data,bar_g_evs,bar_g_att,scatter,events_graph,start_date,end_date)
    return bar_g,scatter,events_graph

def make_pdf(data,bar_evs,bar_att,scatter,timeline,start_date,end_date):
    #write
    #bar1 = pio.write_image(bar_evs,"/Users/temp/Documents/readiness_dashboard/"+"bar1.jpeg")
    #bar2 = pio.write_image(bar_att,"/Users/temp/Documents/readiness_dashboard/"+"bar2.jpeg")
    #scat = pio.write_image(scatter,"/Users/temp/Documents/readiness_dashboard/"+"scatter.jpeg")
    bar1 = pio.write_image(bar_evs,"https://raw.githubusercontent.com/CappucciNOPE/oepr_dashboard/main/"+"bar1.jpeg")
    bar2 = pio.write_image(bar_att,"https://raw.githubusercontent.com/CappucciNOPE/oepr_dashboard/main/"+"bar2.jpeg")
    scat = pio.write_image(scatter,"https://raw.githubusercontent.com/CappucciNOPE/oepr_dashboard/main/"+"scatter.jpeg")
    #time = pio.write_image(timeline,"time.svg")
    report = FPDF()
    report.set_font("Times", size=20,style='B')
    report.add_page()
    report.cell(txt='Tulane University')
    report.ln()
    report.cell(txt='Office of Emergency Preparedness and Response')
    report.ln()
    report.cell(txt='Incidents and Events Summary')
    report.ln()
    report.cell(txt='Reporting Period: '+str(start_date)+' to '+str(end_date))
    report.ln()
    logo = Image.open("https://raw.githubusercontent.com/CappucciNOPE/oepr_dashboard/main/OEPR_logo.png")
    logoh,logow = logo.size
    report.image("https://raw.githubusercontent.com/CappucciNOPE/oepr_dashboard/main/OEPR_logo.png",w=(report.epw)/2,h=((logoh)*(report.epw/logow))/2)
    report.set_font(size=10)
    report.add_page()
    bar1 = Image.open("https://raw.githubusercontent.com/CappucciNOPE/oepr_dashboard/main/"+"bar1.jpeg")
    b1w, b1h = bar1.size
    bar2 = Image.open("https://raw.githubusercontent.com/CappucciNOPE/oepr_dashboard/main/"+"bar2.jpeg")
    b2w, b2h = bar2.size
    scat = Image.open("https://raw.githubusercontent.com/CappucciNOPE/oepr_dashboard/main/"+"scatter.jpeg")
    scatw, scath = scat.size
    report.image("https://raw.githubusercontent.com/CappucciNOPE/oepr_dashboard/main/"+"bar1.jpeg",w=report.epw,h=(b1h)*(report.epw/b1w))
    report.ln()
    report.image("https://raw.githubusercontent.com/CappucciNOPE/oepr_dashboard/main/"+"bar2.jpeg",w=report.epw,h=(b2h)*(report.epw/b2w))
    report.ln()
    report.image("https://raw.githubusercontent.com/CappucciNOPE/oepr_dashboard/main/"+"scatter.jpeg",w=report.epw,h=(scath)*(report.epw/scatw))
    report.add_page()
    k2p = pd.DataFrame(data.loc[data["Event_Type"].isin(['Monitoring','Incident'])])

    allzip = list(zip(k2p["Key"],k2p['Broad_Event']))
    uzip = pd.unique(allzip)
    keydict = dict(uzip)
    print(keydict)
    for key in keydict.keys():
        k2p = pd.DataFrame(data.loc[data["Event_Type"].isin(['Monitoring','Incident'])])
        report.cell(txt=keydict[key])
        report.ln()
        with report.table(text_align="LEFT") as table:
            selrows = pd.DataFrame(k2p.loc[k2p["Key"]==key])
            selrows.sort_values("Start_Date/Time",inplace=True)
            start_date=selrows.iloc[0]["Start_Date/Time"]
            end_date = selrows["End_Date/Time"].max()
            print(start_date, end_date)
            #k2p=k2p.loc[k2p['Date'] >= start_date]
            #k2p=k2p.loc[k2p['Date'] < end_date]
            i = 0
            header = table.row()
            for col in ["Start_Date/Time","End_Date/Time","Event","Event_Code"]:
                header.cell(col)
            for data_row in range(len(selrows)):
                row = selrows.iloc[i]
                #print(i)
                report_row = table.row()
                i+=1
                for data_col in ["Start_Date/Time","End_Date/Time","Event","Event_Code"]:
                    report_row.cell(str(row[data_col]))
            report.ln()
        #trainings = .loc[d['Event_Type']=='Outreach']
        monitoring = selrows.loc[selrows['Event_Type']=='Monitoring']
        monitoring_events = monitoring.loc[monitoring['Event_Code']=='ME']
        monitoring_status = monitoring.loc[monitoring['Event_Code']=='MS']
        incidents = pd.DataFrame(selrows.loc[selrows['Event_Type']=='Incident'])
        i_comm = pd.DataFrame(incidents.loc[incidents['Event_Code']=='IC'])
        i_ncomm = pd.DataFrame(incidents.loc[incidents['Event_Code']=='IN'])
        events = monitoring.loc[monitoring["Event_Code"]=="EV"]
        # monitoring events graph
        if len(events) > 0 :
            events_graph = px.timeline(events, x_start='Start_Date/Time',x_end='End_Date/Time',y='Department/Organization',text="Event")
            events_graph.update_traces()
            events_graph.update_layout(legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1))
        # monitoring timeline graph
        if len(monitoring_status) > 0:
            monitoring_graph = px.timeline(monitoring_status,x_start='Start_Date/Time',x_end='End_Date/Time',y='Event',color='Event',text="Event")
            monitoring_graph.update_layout(xaxis_range=[start_date,end_date],width=1600, height=400)
            monitoring_graph.update_traces()
            events_graph.add_traces(monitoring_graph.data)
            events_graph.update_layout(legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1))
        # monitoring status event
        if len(monitoring_events) > 0:
            monitoring_events_time = px.scatter(x=monitoring_events['Start_Date/Time'],y=monitoring_events['Department/Organization'],text=monitoring_events['Event'])
            monitoring_events_time.update_traces(marker_size=10)
            events_graph.add_traces(monitoring_events_time.data)  
            events_graph.update_layout(legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1)) 
        # scatters for everbridge, for monitoring events, and for incidents  
        if len(i_comm) > 0:
            ever_graph = px.scatter(x = i_comm['Start_Date/Time'],y = i_comm['Department/Organization'],text=i_comm['Event'])
            ever_graph.update_traces(marker_size=10)
            events_graph.add_traces(ever_graph.data)
            events_graph.update_layout(legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1))

        if len(i_ncomm) > 0:
            incident_p = px.scatter(x=i_ncomm['Start_Date/Time'],y=i_ncomm['Department/Organization'],text=i_ncomm['Event'])
            incident_p.update_traces(marker_size=10)
            events_graph.add_traces(incident_p.data)
            events_graph.update_layout(legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1))
        if (len(i_ncomm) > 0) or (len(monitoring_events)>0) or (len(monitoring_status)>0) or (len(i_comm)>0) or (len(events)>0):
            ev = pio.write_image(events_graph,"https://raw.githubusercontent.com/CappucciNOPE/oepr_dashboard/main/"+str(key)+".jpeg")
            ev = Image.open("https://raw.githubusercontent.com/CappucciNOPE/oepr_dashboard/main/"+str(key)+".jpeg")
            evw, evh = ev.size
            report.image("https://raw.githubusercontent.com/CappucciNOPE/oepr_dashboard/main/"+str(key)+".jpeg",w=report.epw,h=(evh)*(report.epw/evw))
        report.add_page()
    ft = pio.write_image(timeline,"https://raw.githubusercontent.com/CappucciNOPE/oepr_dashboard/main/"+"timeline.jpeg")
    ft = Image.open("https://raw.githubusercontent.com/CappucciNOPE/oepr_dashboard/main/"+"timeline.jpeg")
    ftw, fth = ft.size
    fulltime = report.image("https://raw.githubusercontent.com/CappucciNOPE/oepr_dashboard/main/"+"timeline.jpeg",w=report.epw,h=(fth)*(report.epw/ftw))
    report.output("https://raw.githubusercontent.com/CappucciNOPE/oepr_dashboard/main/test.pdf")
    
        
        
        
'''To Crash when the the server won't stop'''
#os.kill(os.getpid(),signal.SIGTERM)


if __name__ =='__main__':
    app.run_server(debug=True)
