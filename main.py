#libraries
from pymongo import MongoClient
import pandas as pd
import numpy as np
import plotly.express as px
from statistics import mean
import streamlit as st
from unidecode import unidecode

#mongodb connection
client = MongoClient(st.secrets['url_con'])
db = client.football_data
col = db.fotmob_stats

cups = ['INT', 'INT-2']

#get data from mongodb database
@st.cache_data(show_spinner=False)
def get_stats(cups: list, team: str) -> list:
    stats = list(col.aggregate([{"$match": {"general.country": {"$nin": cups}, "$or": [{"teams.home.name": team}, {"teams.away.name": team}]}}, 
                       {"$project": {"_id": 0, "general.round": 1, "general.league": 1,"teams.home.name": 1, "teams.away.name": 1, "stats": 1, 'result': 1}}]))
    print(stats[0])
    return stats

#get percentage
def get_perc(x: float, y: float) -> float:
    perc = np.round(((x / y) - 1) * 100, 2)

    if perc == 1:
        perc = 0.0
    
    return perc

#create dataframe from data obtained from mongodb
def get_dataframe(squad_stats: list, team:str) -> pd.DataFrame:
    matchweeks = []
    venues = []
    opps = []
    bp_diff = []
    pass_op_diff = []
    xg_op_diff = []
    touch_opp_diff = []
    results = []

    

    for stat in squad_stats:
        matchweek = int(stat['general']['round'][6:]) if len(stat['general']['round']) > 6 else int(stat['general']['round'])
        
        if matchweek > 5:
            
            home = stat['teams']['home']['name']
            away = stat['teams']['away']['name']
        
            opp = away if home == team else home
    
            venue = 'home' if home == team else 'away'
            venue_opp = 'away' if home == team else 'home'
                
            bp = stat['stats']['ball_possession'][venue_opp]
            pass_op = stat['stats']['passes_opp_half_%'][venue_opp]
            xg_op = stat['stats']['xg_op_for_100_passes'][venue_opp]
            touch_opp = stat['stats']['touch_opp_box_100_passes'][venue_opp]
            

            if stat['result'] == venue:
                result = 'Win'
            elif stat['result'] == venue_opp:
                result = 'Loss'
            else:
                result = 'Draw'

            opps.append(opp)
            matchweeks.append(matchweek)
            venues.append(venue.title())
            results.append(result)
            
            bp_opp = []
            pass_op_opp = []
            xg_op_opp = []
            touch_opp_opp = []

            opp_stats = get_stats(cups=cups, team=opp)
            for stat_opp in opp_stats:                    
                matchweek_opp = int(stat_opp['general']['round'][6:]) if len(stat_opp['general']['round']) > 6 else int(stat_opp['general']['round'])
                if matchweek_opp < matchweek:
                    home = stat_opp['teams']['home']['name']
                    venue = 'home' if home == opp else 'away'
    
                    bp_opp.append(stat_opp['stats']['ball_possession'][venue])
                    pass_op_opp.append(stat_opp['stats']['passes_opp_half_%'][venue])
                    xg_op_opp.append(stat_opp['stats']['xg_op_for_100_passes'][venue])
                    touch_opp_opp.append(stat_opp['stats']['touch_opp_box_100_passes'][venue])
                else:
                    continue

            bp_diff.append(get_perc(bp, mean(bp_opp)))
            pass_op_diff.append(get_perc(pass_op, mean(pass_op_opp)))
            xg_op_diff.append(get_perc(xg_op, mean(xg_op_opp)))
            touch_opp_diff.append(get_perc(touch_opp, mean(touch_opp_opp)))

    df = pd.DataFrame({
        "Matchweek": matchweeks, 
        "Venue": venues, 
        "Result": results,
        "Opponent": opps,
        "Ball Poss Diff %": bp_diff, 
        "Pass Opp Half Diff %": pass_op_diff, 
        "xG Open Play 100 Passes Diff %": xg_op_diff, 
        "Touch Opp Box 100 Passes Diff %": touch_opp_diff
    }) 

    df['Overall Diff %'] = df.iloc[:, 4:].mean(axis=1)
    df['Weighted Avg Diff %'] = (df['Ball Poss Diff %'] * 0.12) + (df['Pass Opp Half Diff %'] * 0.25) + (df['xG Open Play 100 Passes Diff %'] * 0.4) + (df['Touch Opp Box 100 Passes Diff %'] * 0.32)
    df['Standard Dev'] = df.iloc[:, 4:8].std(axis=1)

    return df.sort_values(by='Matchweek')

st.set_page_config(
    page_title='Squad Report', 
    layout='wide', 

)

with st.sidebar:
    st.image('icon_img/image.jpeg', 
             caption="Saulo Faria - Data Scientist Specialized in Football")
    st.write(f"This App was designed in order to get an overview of squads")

    st.subheader("My links (pt-br)")
    st.link_button("Aposta Consciente", "https://apostaconsciente.hotmart.host/product-page-88be95cc-1892-4fa6-b364-69a271150f8f", use_container_width=True)
    #st.link_button("Udemy", "https://www.udemy.com/user/saulo-faria-3/", use_container_width=True)
    st.link_button("Instagram", "https://www.instagram.com/saulo.foot/", use_container_width=True)
    st.link_button("X", "https://x.com/fariasaulo_", use_container_width=True)
    st.link_button("Youtube", "https://www.youtube.com/channel/UCkSw2eyetrr8TByFis0Uyug", use_container_width=True)
    st.link_button("LinkedIn", "https://www.linkedin.com/in/saulo-faria-318b872b9/", use_container_width=True)

st.title("Squad Report Based on Relative Performance")
st.subheader("How much opponents lose their average performance against the selected squad?")
st.write("Except from Standard Deviation, all metrics are shown in a lower-is-better mode")

squads = col.distinct('teams.home.name')


try:
            
            squad = st.selectbox(label='Select a Squad', options=squads, index=21)
            squad_data = col.find_one({'teams.home.name': squad})
   
            stats = get_stats(cups=cups, team=squad)
            df = get_dataframe(stats, team=squad)
            print(df)

            df_styled = df.style.background_gradient(cmap='RdBu_r', text_color_threshold=0.5, 
                                                        subset=df.columns[4:10], low=0.00).background_gradient(cmap='Blues_r', 
                                                                                                                text_color_threshold=0.5, 
                                                                                                                subset=df.columns[-1:], vmin=0).format(precision=2)

            st.divider()
            
            col1, col2, col3, col4, col5 = st.columns(5, vertical_alignment='center')

            with col1:
                st.image(f"{squad_data['teams']['home']['image']}")

            with col2:
                st.metric(label="Last 5 xG Open Play for 100 Passes Diff %", value=np.round(df.tail(5)['xG Open Play 100 Passes Diff %'].mean(), 2))

            with col3:
                st.metric(label="Last 5 Pass Opp Half Diff %", value=np.round(df.tail(5)['Pass Opp Half Diff %'].mean(), 2))

            with col4:
                st.metric(label="Last 5 Weighted Avg Diff %", value=np.round(df.tail(5)['Weighted Avg Diff %'].mean(), 2))

            with col5:
                st.metric(label="Last 5 Standard Deviation", value=np.round(df.tail(5)['Standard Dev'].mean(), 2))

            st.divider()
                

                
            st.dataframe(df_styled, hide_index=True)
                
            st.divider()

            st.subheader(f"{squad} TreeMap")
            st.write('Size of opponents squares are based on Standard Deviation')

            fig_tree = px.treemap(data_frame=df, path=[px.Constant(squad_data['general']['league']), 'Result', 'Venue', 'Opponent'], values='Standard Dev', 
                                      color='Weighted Avg Diff %', color_continuous_scale='RdBu_r')
            fig_tree.update_traces(marker=dict(cornerradius=5))
            fig_tree.update_layout(margin = dict(t=5, l=5, r=1, b=5))
            st.plotly_chart(fig_tree, theme='streamlit')

            st.divider()

            col6, col7 = st.columns(2)

                #chart1
            with col6:
                fig = px.box(data_frame=df, x='Venue', y='Weighted Avg Diff %', color='Venue',
                                color_discrete_sequence=['#073271', '#7e3707'], category_orders={'Venue': ['Home', 'Away']})
                    
                st.plotly_chart(fig, theme='streamlit')

                #chart2
            with col7:
                fig2 = px.scatter(data_frame=df, x='Standard Dev', y='Weighted Avg Diff %', color='Matchweek', opacity=0.75, 
                                    color_continuous_scale='blues', hover_name='Opponent')
                fig2.update_traces(marker=dict(size=20,
                                    line=dict(width=2,
                                                color='DarkSlateGrey')),
                        selector=dict(mode='markers'))
                fig2.add_vline(x=15)
                fig2.add_hline(y=0)
                fig2.update_yaxes(tick0=-100, dtick=30)
                fig2.update_xaxes(tick0=0, dtick=10)               


                st.plotly_chart(fig2, theme='streamlit')                


except Exception as e:
    st.text(e)
    st.write("Ops! Something Went Wrong! - Maybe You've Chosen a League which Hasn't Started Yet Or Has Less Than 6 Matchweeks.")
    
st.caption("Created by Saulo Faria - Data Scientist Specialized in Football")
           
