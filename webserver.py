import streamlit as st
import pandas as pd
import get_data

st.title('External Data Finder')
st.header('Instructions')
st.write('Detailed instructions can be found in the paper "Data-driven decision-making: The use of external data" (to be published). Point to the question marks by each input field to get additional hel.')

st.header('Background information')
st.write('Enter keywords separated by spaces.')
problem = st.text_input('Problem domain', help='Define the context for the decision. Examples include hiring, optimising a production line, or marketing.')
decision = st.text_input('Decision', help='Input a decision in the chosen problem domain.')
bp = st.text_input('Business process', help='Name the appropriate business process.')
domain = st.text_input('Domain components', help='Based on the problem domain, list the components involved. Here, a component is defined as an entity that is integral to the problem domain. Examples include products, services, or roles. The purpose of this step is to widen the context in the search for external data, i.e. to try to include useful information that are not necessarily part of the current business process. A useful approach to finding these components is to put the current business process in a larger context, and see what kind of services, products, or roles come into the picture.')
st.header('Search query')
st.write('Enter search keywords in order of most important to least important.')
q = st.text_input('Search query')
st.header('Portals to search')
eu = st.checkbox('EU Data Portal')
kaggle = st.checkbox('Kaggle')
datahub = st.checkbox('Datahub.io')
datagov = st.checkbox('Data.gov (US)')


if st.button('Search') and (eu or kaggle or datahub or datagov):
    bg = problem + ' ' + decision + ' ' + bp + ' ' + domain
    query = q
    get_data.init()
    datasets = []
    if eu: datasets.extend(get_data.query(get_data.eu, query, bg))
    if kaggle: datasets.extend(get_data.query(get_data.kaggle, query, bg))
    if datahub: datasets.extend(get_data.query(get_data.datahub, query, bg))
    if datagov: datasets.extend(get_data.query(get_data.datagov, query, bg))
    get_data.shutdown()
    data = []
    for d in datasets:
        data.append([d.name, d.url, d.source, d.c_score])
    df = pd.DataFrame(data=data, columns=['Dataset', 'URL', 'Source', 'Score'])
    df.sort_values(by=['Score'], ascending=False, inplace=True)
    for i in range(len(df)):
        s = f'<a href="{df.iloc[i, 1]}">{df.iloc[i, 0]}</a>'
        df.at[i, 'Dataset'] = s
    df = df.drop(columns=['URL'])
    st.write(df.to_html(justify='left', escape=False, index=False), unsafe_allow_html=True)