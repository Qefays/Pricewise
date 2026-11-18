"""JSON-only business comparisons over validated, exact-item observations."""
import math
import html
import pandas as pd
import streamlit as st

TEAL='#087f78'
BLUE='#5586ad'
AMBER='#bd7b1c'

def savings_summary(complete, reference_code):
    """Reference must be an observed complete basket, never a partial sum."""
    if complete.empty or reference_code not in complete.premise_code.values:
        return None
    baseline=float(complete.set_index('premise_code').loc[reference_code,'total'])
    best=float(complete.total.min())
    if not math.isfinite(baseline) or not math.isfinite(best) or baseline<=0 or best<=0:
        return None
    return {'reference':baseline,'best':best,'highest':float(complete.total.max()),
            'gross':baseline-best,'percent':100*(baseline-best)/baseline}

def base_option():
    return {'animation':False,'aria':{'enabled':True},'tooltip':{'trigger':'item','confine':True},
            'grid':{'left':12,'right':64,'top':20,'bottom':45,'containLabel':True},
            'textStyle':{'fontFamily':'Segoe UI'},'color':[TEAL,BLUE,AMBER,'#936b9c']}

def ranking_spec(frame, value='total'):
    frame=frame.sort_values([value,'premise_code']).head(15)
    spec=base_option()
    labels=[f"{str(r['premise'])[:28]} · #{r['premise_code']}" for _,r in frame.iterrows()]
    spec.update(xAxis={'type':'value','name':'RM','min':0},
                yAxis={'type':'category','inverse':True,'data':labels,'axisLabel':{'width':145,'overflow':'truncate'}},
                series=[{'type':'bar','barMaxWidth':24,'data':[{'value':round(float(v),2),'label':{'formatter':f'RM {v:.2f}'},'tooltip':{'formatter':html.escape(str(frame.iloc[i]['premise']))+f'<br/>RM {v:.2f}'},'itemStyle':{'color':TEAL if v==frame[value].min() else BLUE}} for i,v in enumerate(frame[value])],
                         'label':{'show':True,'position':'right','formatter':'RM {c}'},
                         'tooltip':{'formatter':'{b}<br/>RM {c}'}}])
    return spec

def render_ranking(frame,value='total',key='basket_business_rank'):
    st.echarts_chart(ranking_spec(frame,value),height=max(240,min(len(frame),15)*35+70),key=key,renderer='svg')

def basket_business_views(rows,complete,shops,items):
    if complete.empty:return
    with st.container(border=True):
        st.subheader('Compare your basket')
        st.caption('Every total covers your full list and quantities. Up to 15 lowest-cost complete outlets are ranked.')
        mode=st.segmented_control('Comparison view',['Basket totals','Product prices','Price heatmap','Category spend'],default='Basket totals',key='business_view') or 'Basket totals'
        ranked=complete.merge(shops[['premise_code','premise']],on='premise_code')
        if mode=='Basket totals':
            render_ranking(ranked)
            st.caption('Teal bars identify the lowest observed total, including ties. Bars start at zero.')
            return
        names=ranked.set_index('premise_code').premise.to_dict()
        if 'business_outlets' in st.session_state:
            st.session_state['business_outlets']=[c for c in st.session_state['business_outlets'] if c in names]
        choices=st.multiselect('Outlets to compare',ranked.premise_code.tolist(),default=ranked.head(3).premise_code.tolist(),max_selections=5,format_func=lambda c:f'{names[c]} · #{c}',key='business_outlets')
        if not choices:
            st.info('Select at least one outlet to compare.');return
        subset=rows[rows.premise_code.isin(choices)].copy()
        all_codes=list(dict.fromkeys(subset.item_code.tolist()))
        lookup=items.set_index('item_code')
        if 'business_items' in st.session_state:
            st.session_state['business_items']=[c for c in st.session_state['business_items'] if c in all_codes]
        codes=st.multiselect('Products in this chart',all_codes,default=all_codes[:8],format_func=lambda c:f"{lookup.loc[c,'item']} · {lookup.loc[c,'unit']}",key='business_items')
        if not codes:
            st.info('Choose at least one basket product.');return
        subset=subset[subset.item_code.isin(codes)]
        spec=base_option()
        outlet_labels=[f'{str(names[c])[:24]} · #{c}' for c in choices]
        product_labels=[f'#{c} · {str(lookup.loc[c,"item"])[:30]} · {lookup.loc[c,"unit"]}' for c in codes]
        spec['grid'].update(top=70,bottom=90,right=25)
        if mode=='Price heatmap':
            values=[]
            for y,c in enumerate(codes):
                for x,p in enumerate(choices):
                    found=subset[(subset.item_code==c)&(subset.premise_code==p)]
                    if not found.empty:values.append({'value':[x,y,round(float(found.price.iloc[0]),2)],'label':{'formatter':f'{float(found.price.iloc[0]):.2f}'},'tooltip':{'formatter':html.escape(product_labels[y])+'<br/>'+html.escape(outlet_labels[x])+f'<br/>RM {float(found.price.iloc[0]):.2f}'}})
            low=min(v['value'][2] for v in values)
            high=max(v['value'][2] for v in values)
            if low==high:st.caption(f'All displayed prices are RM {low:.2f}; there is no price variation in this selection.')
            spec.update(xAxis={'type':'category','data':outlet_labels,'axisLabel':{'rotate':25,'width':100,'overflow':'truncate'}},
                        yAxis={'type':'category','data':product_labels,'axisLabel':{'width':150,'overflow':'truncate'}},
                        visualMap={'min':low,'max':high if high>low else low+0.01,'show':high>low,'orient':'horizontal','left':'center','top':0,'calculable':True,'inRange':{'color':['#e3f2ee',TEAL]}},
                        series=[{'type':'heatmap','data':values,'label':{'show':True},'tooltip':{'formatter':'Observed price (RM): {c}'}}])
            st.caption('Cell labels are RM per listed purchase unit, before basket quantity. Colours use an absolute RM scale across different products; compare outlets within the same row. Blank cells mean no observation, never zero.')
        else:
            field='price' if mode=='Product prices' else 'line_total'
            if mode=='Category spend':
                subset['category']=subset.item_code.map(lookup.item_category)
                groups=subset.groupby(['category','premise_code'],observed=True).line_total.sum().unstack()
                labels=groups.index.astype(str).tolist()
                st.caption('Expenditure for the chart-selected basket products, grouped by official category; quantities are included.')
            else:
                groups=subset.pivot(index='item_code',columns='premise_code',values='price').reindex(codes)
                labels=product_labels
                st.caption('Compare bars within each product group. Each price uses that product’s exact code and listed unit; quantities are not included.')
            spec.update(legend={'type':'scroll','top':0},xAxis={'type':'category','data':labels,'axisLabel':{'rotate':25,'width':115,'overflow':'truncate'}},yAxis={'type':'value','name':'RM','min':0},
                        series=[{'type':'bar','name':outlet_labels[i],'barMaxWidth':30,'data':[None if pd.isna(v) else round(float(v),2) for v in groups.reindex(columns=choices)[p]],'tooltip':{'formatter':'{a}<br/>{b}<br/>RM {c}'}} for i,p in enumerate(choices)])
        st.echarts_chart(spec,height=max(380,len(codes)*38+140) if mode=='Price heatmap' else 400,key='basket_business_detail',renderer='svg')
        with st.expander('Chart data · exact products, quantities and dates'):
            from pricewise_ui import table
            table(subset[['item','unit','quantity','price','line_total','premise','date','age_days']])
