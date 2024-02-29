import streamlit as st
import pandas as pd
from google.oauth2 import service_account
from googleapiclient.discovery import build
from io import BytesIO
import numpy as np

# Retrieve credentials from Streamlit secrets
credentials_dict = st.secrets["google_drive_credentials"]

try:
    credentials = service_account.Credentials.from_service_account_info(
        credentials_dict,
        scopes=["https://www.googleapis.com/auth/drive"]
    )
    st.write("欢迎")

    # Build the Google Drive API service
    drive_service = build('drive', 'v3', credentials=credentials)
except Exception as e:
    st.error(f"Error loading credentials: {e}")
    drive_service = None

# Function to read the contents of the specified file
def read_drive_file(file_name):
    if drive_service is None:
        st.error("Drive service is not available.")
        return None

    results = drive_service.files().list(
        q=f"name='{file_name}'", pageSize=1, fields="files(id, name)"
    ).execute()

    items = results.get('files', [])
    if not items:
        st.error(f"File '{file_name}' not found in Google Drive.")
        return None

    file_id = items[0]['id']
    request = drive_service.files().get_media(fileId=file_id)
    file_content = request.execute()

    return file_content

# Read the contents of "production.csv"
file_name = "production.csv"
file_content = read_drive_file(file_name)

# If file content is available, display it as a DataFrame
if file_content:
    df = pd.read_csv(BytesIO(file_content))

    # Display data in Streamlit app    
    st.markdown(
        """<h1 style='text-align: center; color: royalblue;'>跳线生产分析</h1>""",
        unsafe_allow_html=True
    )

    # Assuming 'Date' is a column in your DataFrame
    df['Date'] = pd.to_datetime(df['Date'])

    # Set pandas options to display all columns and expand the width of the 'Steps' column
    pd.set_option('display.max_columns', None)
    pd.set_option('display.max_colwidth', None)

    # Create tabs using st.radio()
    tab_selection = st.radio("选择选项卡", ["入库详情", "生产日期筛选","不良率详情","生产种类筛选","生产工时详情"])

    # Define result_df 
    grouped_df = df.groupby(["Manufacture_number","Type", "Color", "Length", "Order_number"])
    tables = []
    for name, group in grouped_df:
        total_time_per_person = group["Time_per_person"].sum()
        total_production_time=group["Total_time"].sum()
        total_production_number = group[group['End_Steps'].str.contains('storage', case=False, na=False)]['Production_number'].sum()
        last_step = group.iloc[-1]["End_Steps"]
        date=group.iloc[-1]["Date"]
        result_table = {
            "Date": date,    
            "Manufacture_number": name[0],
            "Type": name[1],
            "Color": name[2],
            "Length": name[3],
            "Order_number": name[4],
            "Total_production_number": total_production_number,
            "Last_step": last_step
        }
        tables.append(result_table)
    result_df = pd.DataFrame(tables)
    result_df['Date'] = result_df['Date'].dt.strftime('%Y-%m-%d')
    result_df['Order_number'] = result_df['Order_number'].astype(int)

    # Define result_df 
    grouped_df1 = df.groupby(["Manufacture_number","Type", "Color", "Length","Order_number"])
    tables1 = []
    for name, group in grouped_df1:
       total_production_time= group["Total_time"].sum()
       total_people=group["People"].sum()
       last_step = group.iloc[-1]["End_Steps"]
       date=group.iloc[-1]["Date"]
       total_production_number = group[group['End_Steps'].str.contains('storage', case=False, na=False)]['Production_number'].sum()
       result_table1 = {
           "Date": date,    
           "Manufacture_number": name[0],
           "Type": name[1],
           "Color": name[2],
           "Length": name[3],
           "Order_number": name[4],
           "Total_people": total_people,
           "Total_production_time": total_production_time,
           "Last_step": last_step
       }
       tables1.append(result_table1)  # Corrected variable name
    result_df1 = pd.DataFrame(tables1)
    result_df1['Date'] = pd.to_datetime(result_df1['Date']).dt.strftime('%Y-%m-%d')  # Convert to datetime and then format
    result_df1_filtered = result_df1[result_df1['Date'] > '2024-02-02']  # Filter based on 'Date' column


    
    if tab_selection == "不良率详情":
         # Warning Section
        st.markdown("<h1 style='text-align: center;'>总不良率</h1>", unsafe_allow_html=True)
        # Convert 'Mistake_rates' column to numeric, handling errors with coerce
        df['Mistake_rates'] = pd.to_numeric(df['Mistake_rates'], errors='coerce')

        # Group by year and month to calculate yearly and monthly abnormal counts
        yearly_abnormal_counts = []
        monthly_abnormal_counts = []

        for year in [2023, 2024]:
            for month in range(1, 13):
                filtered_df = df[(df['Date'].dt.year == year) & (df['Date'].dt.month == month)]
                abnormal_rows = filtered_df['Mistake_rates'].ge(0.02) & ~filtered_df['Mistake_rates'].isna()
                total_abnormal_monthly = abnormal_rows.sum()
                monthly_abnormal_counts.append({"Year": year, "Month": month, "Total Abnormal": total_abnormal_monthly})
        
            # Calculate yearly total abnormal counts
            total_abnormal_yearly = sum(monthly_abnormal_count["Total Abnormal"] for monthly_abnormal_count in monthly_abnormal_counts if monthly_abnormal_count["Year"] == year)
            yearly_abnormal_counts.append({"Year": year, "Total Abnormal": total_abnormal_yearly})

        # Display yearly total abnormal counts
        st.subheader("年度不良率统计")
        yearly_abnormal_table = pd.DataFrame(yearly_abnormal_counts)

        # Display yearly abnormal counts in a table
        st.table(yearly_abnormal_table)
        
        # Display monthly abnormal counts for each year
        st.subheader("月度不良率统计")
        for year in [2023, 2024]:
            st.subheader(f"{year} 年")
            monthly_abnormal_table_year = pd.DataFrame([entry["Total Abnormal"] for entry in monthly_abnormal_counts if entry["Year"] == year], columns=["Total Abnormal"])
            st.bar_chart(monthly_abnormal_table_year, use_container_width=True)

        # Sidebar widget to select the year and month
        selected_year = st.sidebar.selectbox("选择年份", [2023, 2024])
        selected_month = st.sidebar.selectbox("选择月份", range(1, 13))

        # Filter the DataFrame based on the selected year and month
        filtered_df = df[(df['Date'].dt.year == selected_year) & (df['Date'].dt.month == selected_month)]

        # Warning Section
        st.markdown("<h1 style='text-align: center;'>不良率详情</h1>", unsafe_allow_html=True)
        # Convert 'Mistake_rates' column to numeric, handling errors with coerce
        filtered_df['Mistake_rates'] = pd.to_numeric(filtered_df['Mistake_rates'], errors='coerce')

        st.subheader(f"{selected_year} 年 {selected_month} 月的详细不良率统计")

        # Define the threshold for abnormal rates
        threshold = st.sidebar.slider("设置阈值:", 0.0, 0.1, 0.02, 0.01)

        # Display detailed abnormal rates categorized by ranges (0.01 intervals) larger than the threshold
        for i in range(int(threshold * 100), 10):
            lower_bound = i / 100
            upper_bound = (i + 1) / 100
            range_df = filtered_df[(filtered_df['Mistake_rates'] >= lower_bound) & (filtered_df['Mistake_rates'] < upper_bound)]
            if not range_df.empty:
                st.write(f"不良率范围: {lower_bound} - {upper_bound}")
                st.write(range_df)

    # Third Tab: Data Filtering
    elif tab_selection == "生产日期筛选":
        # Filter Data 1
        st.sidebar.title("选取生产数据")
        # Add a selectbox for month and year filtering
        selected_month = st.sidebar.selectbox("选择月份", range(1, 13), format_func=lambda x: f"{x:02d}")  # Format month with leading zero
        selected_year = st.sidebar.selectbox("选择年份", range(2023, 2025))
        # Filter the DataFrame based on selected month and year
        filtered_by_date_df = df[
            (df['Date'].dt.month == int(selected_month)) & (df['Date'].dt.year == int(selected_year))
        ]   
        filtered_by_date_df['Date'] = filtered_by_date_df['Date'].dt.strftime('%Y-%m-%d')
        filtered_by_date_df['Order_number'] = filtered_by_date_df['Order_number'].astype(int)
        filtered_by_date_df = filtered_by_date_df.loc[:, ~filtered_by_date_df.columns.str.startswith('Unnamed')]
        if st.sidebar.button("按日期过滤"):
            # Display the filtered DataFrame
            st.subheader("按日期过滤结果")
            st.write(filtered_by_date_df)

    elif tab_selection == "生产种类筛选":
        # Filter Data Section 2
        st.sidebar.title("选择跳线数据")
        manufacture_number= st.sidebar.selectbox("选择制令单号", [''] + sorted(df['Manufacture_number'].unique().tolist()))
        cable_type = st.sidebar.selectbox("选择跳线种类", [''] + sorted(df['Type'].unique().tolist()))
        color = st.sidebar.selectbox("选择颜色", [''] + sorted(df['Color'].astype(str).unique().tolist()))
        length = st.sidebar.selectbox("选择长度", [''] + sorted(df['Length'].astype(str).unique().tolist()))

        def filter_data(df, manufacture_number=None, cable_type=None, length=None, color=None):
            filtered_data = df.copy()
            if manufacture_number:
                filtered_data = filtered_data[filtered_data['Manufacture_number'] ==manufacture_number]
            if cable_type:
                filtered_data = filtered_data[filtered_data['Type'] == cable_type]
            if length:
                filtered_data = filtered_data[filtered_data['Length'].astype(str) == length]
            if color:
                color = color.lower()  # Convert user input to lowercase
                filtered_data = filtered_data[filtered_data['Color'].astype(str).str.lower() == color]

            return filtered_data

        if st.sidebar.button("获取筛选数据结果"):
            filtered_df = filter_data(df, manufacture_number, cable_type, length, color)
            filtered_df['Date'] = filtered_df['Date'].dt.strftime('%Y-%m-%d')
            filtered_df['Order_number'] = filtered_df['Order_number'].astype(int)
            filtered_df = filtered_df.dropna(axis=1, how='all')
            st.subheader(f"{cable_type}, {length}, {color} 筛选数据展示")
            st.write(filtered_df)
            if filtered_df.empty:
                st.info("No matching entries.")


    # Fourth Tab: Production Details
    elif tab_selection == "入库详情":
        # Create a dropdown menu for selecting "已入库" or "未入库"
        selected_option = st.selectbox("选择入库详情", ["未入库", "已入库"])

        # Filter and sort the DataFrame based on the selected option
        if selected_option == "已入库":
            filtered_df = result_df[result_df['Last_step'].str.contains('storage', case=False, na=False) &
                        (result_df['Order_number'] == result_df['Total_production_number'])].sort_values(by='Date')
            # Display the filtered DataFrame for '已入库'
            st.markdown("<h2 style='text-align: center;'>已入库结果</h2>", unsafe_allow_html=True)
            st.write(filtered_df)
        elif selected_option == "未入库":
            non_storage_df = result_df[result_df['Order_number'] > result_df['Total_production_number']]
            non_storage_df = non_storage_df.sort_values(by='Date')
            # Display the filtered DataFrame for '未入库'
            st.markdown("<h2 style='text-align: center;'>未入库结果</h2>", unsafe_allow_html=True)
            st.write(non_storage_df)
    elif tab_selection == "生产工时详情":
        result_df1_filtered1  = result_df1_filtered[result_df1_filtered['Last_step'].str.contains('storage', case=False, na=False) &
                        (result_df1_filtered['Order_number'] == result_df1_filtered['Total_production_number'])].sort_values(by='Date')
        st.markdown("<h1 style='text-align: center;'>生产工时详情</h1>", unsafe_allow_html=True)
        st.write(result_df1_filtered1)

  
else:
    st.error("Unable to load data from Google Drive.")

# Reset pandas options to their default values after displaying the DataFrames
pd.reset_option('display.max_columns')
pd.reset_option('display.max_colwidth')
