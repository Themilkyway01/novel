"""
爬取起点中文网出版书籍
"""
import json
import os
import time
from selenium import webdriver
from selenium.webdriver.edge.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
import pymysql

# ---------------------------- 配置 ------------------------------
STATE_FILE = 'publish_progress.json'  # 进度记录文件
CATEGORY_FILE = 'publish_categories.json'  # 子分类列表文件
# cmd "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe" --remote-debugging-port=9777 --user-data-dir="D:\selenium_user_data2"
DEBUGGER_ADDRESS = '127.0.0.1:9777'

# ------------------------- 初始化浏览器 --------------------------
options = Options()
options.debugger_address = DEBUGGER_ADDRESS
driver = webdriver.Edge(options=options)
actions = ActionChains(driver)

# --------------------- 工具函数：加载/保存状态 ---------------------
def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return None

def save_state(state):
    with open(STATE_FILE, 'w', encoding='utf-8') as f:
        json.dump(state, f, ensure_ascii=False, indent=4)

# -------------- 1. 收集所有子分类 URL（若不存在则执行） --------------
if not os.path.exists(CATEGORY_FILE):
    print('正在收集子分类 URL ...')
    driver.get('https://www.qidian.com/all/')
    # 滑动至出版
    actions.move_to_element(driver.find_element(By.XPATH, '/html/body/div[1]/div[6]/div[1]/div[1]/a[3]')).perform()
    time.sleep(2)
    # 定位分类容器
    div_type = driver.find_element(By.XPATH, '/html/body/div[1]/div[6]/div[1]/div[4]/div[1]')
    ul_rows = div_type.find_elements(By.XPATH, './/ul')
    # 存储 {name, url}
    categories = []

    for ul_index in range(len(ul_rows)):
        # 重新获取当前行的 ul（防止页面刷新导致引用过期）
        current_ul = driver.find_elements(By.XPATH, '/html/body/div[1]/div[6]/div[1]/div[4]/div[1]//ul')[ul_index]
        # 获取当前 ul 下的所有 li
        li_elements = current_ul.find_elements(By.XPATH, './/li')

        for li_index, li in enumerate(li_elements, start=1):
            # 跳过第一个“全部”
            if ul_index == 0 and li_index == 1:
                time.sleep(2)
                continue

            # 重新获取
            li = driver.find_element(
                By.XPATH, f'/html/body/div[1]/div[6]/div[1]/div[4]/div[1]/ul[{ul_index + 1}]/li[{li_index}]'
            )

            cate_name = li.text
            cate_href = li.find_element(By.XPATH, './a').get_attribute('href')
            categories.append({
                'name': cate_name,
                'href': cate_href
            })

    with open(CATEGORY_FILE, 'w', encoding='utf-8') as f:
        json.dump(categories, f, ensure_ascii=False, indent=4)
    print(f'已收集 {len(categories)} 个子分类，保存至 {CATEGORY_FILE}')

# --------------------- 2. 加载分类列表和进度状态 ---------------------
with open(CATEGORY_FILE, 'r', encoding='utf-8') as f:
    categories = json.load(f)

state = load_state()
if state:
    print(f"发现上次进度：categories {state['cate_idx']}，page {state['page']}，rid {state['item_rid']}")
    start_cate = state['cate_idx']
    start_page = state['page']
    start_item = state['item_rid']
else:
    print("未找到进度文件，从头开始")
    start_cate = 0
    start_page = 1
    start_item = 1

# ------------------------ 3. 连接数据库 --------------------------
conn = pymysql.connect(
    host='localhost',
    user='root',
    password='123456',
    database='novel_data',
    charset='utf8mb4'
)
cursor = conn.cursor()

# 创建数据表（如果不存在）
create_table_sql = """
    CREATE TABLE IF NOT EXISTS publish_book (
        id INT AUTO_INCREMENT PRIMARY KEY,
        img VARCHAR(500) COMMENT '封面',
        name VARCHAR(255) COMMENT '作品名',
        author VARCHAR(255) COMMENT '作者',
        up_time VARCHAR(50) COMMENT '更新时间',
        up_chapter VARCHAR(255) COMMENT '更新章节',
        category VARCHAR(100) COMMENT '分类',
        wordcount INT COMMENT '总字数',
        all_recommend INT COMMENT '总推荐数',
        week_recommend INT COMMENT '周推荐数',
        introduction TEXT COMMENT '简介',
        chapters INT COMMENT '总章节数'
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='起点出版图书表';
"""
cursor.execute(create_table_sql)
conn.commit()

# --------------------- 4. 遍历分类，抓取详情页 ---------------------
for cate_idx, cate in enumerate(categories):
    # 跳过已完成的分类
    if cate_idx < start_cate:
        continue

    cate_url = cate['href']
    print(f"正在爬取分类：{cate['name']} ({cate_url})")

    # 如果是分类继续，则从记录页码开始；否则从第1页开始
    current_page = start_page if cate_idx == start_cate else 1

    # 获取该类别的总页码
    driver.get(cate_url)
    total_page = driver.find_elements(By.XPATH, '//*[@id="page-container"]/div/ul//li')[-2]
    time.sleep(1)

    # 循环页码
    for page in range(current_page, int(total_page.text) + 1):
        print(f'正在爬取第 {page} 页')

        if page != 1:
            page_url = cate_url.rstrip('/') + f'-page{page}/'
            driver.get(page_url)
        else:
            page_url = cate_url
        time.sleep(1)

        # 如果是分类继续，则从记录详情页开始；否则从第1个详情页开始
        start_rid = start_item if (cate_idx == start_cate and page == start_page) else 1

        # 遍历当前页的书籍列表
        for rid in range(start_rid, 21):
            try:
                # 定位书籍详情链接
                detail_link = driver.find_element(By.XPATH, f'//*[@id="book-img-text"]/ul/li[{rid}]/div[1]/a')
                detail_href = detail_link.get_attribute('href')
            except:
                print(f'第 {page} 页第 {rid} 详情页不存在，可能已到页尾')
                break

            # 在新标签页打开详情页
            original_window = driver.current_window_handle
            driver.switch_to.new_window('tab')
            driver.get(detail_href)
            time.sleep(3)

            # 提取所需数据
            try:
                img = driver.find_element(By.XPATH, '//*[@id="bookImg"]/img').get_attribute('src')
                name = driver.find_element(By.XPATH, '//*[@id="bookName"]').text
            except:
                driver.close()
                driver.switch_to.window(original_window)
                time.sleep(1)
                continue

            if len(driver.find_elements(By.XPATH, '//*[@id="book-detail"]/div[5]/div[2]/div/div[1]/p[1]//span')) == 2:
                author = driver.find_element(By.XPATH, '//*[@id="book-detail"]/div[5]/div[2]/div/div[1]/p[1]/span[1]').text
                up_time = driver.find_element(By.XPATH, '//*[@id="book-detail"]/div[5]/div[2]/div/div[1]/p[1]/span[2]').text
            else:
                author = '作者:佚名'
                up_time = driver.find_element(By.XPATH, '//*[@id="book-detail"]/div[5]/div[2]/div/div[1]/p[1]/span[1]').text

            up_chapter = driver.find_element(By.XPATH, '//*[@id="book-detail"]/div[5]/div[2]/div/div[1]/a').text
            category = cate['name']
            wordcount = driver.find_element(By.XPATH, '//*[@id="book-detail"]/div[5]/div[2]/div/div[1]/p[3]/em[1]').text
            all_recommend = driver.find_element(By.XPATH, '//*[@id="book-detail"]/div[5]/div[2]/div/div[1]/p[3]/em[2]').text
            week_recommend = driver.find_element(By.XPATH, '//*[@id="book-detail"]/div[5]/div[2]/div/div[1]/p[3]/em[3]').text
            introduction = driver.find_element(By.XPATH, '//*[@id="book-intro-detail"]').text
            chapters = driver.find_element(By.XPATH, '//*[@id="bookCatalogSection"]/div[1]/p/span').text

            wordcount = int(float(wordcount[:-1]) * 10000) if wordcount[-1] == '万' else int(wordcount)
            all_recommend = int(float(all_recommend[:-1]) * 10000) if all_recommend[-1] == '万' else int(all_recommend)
            week_recommend = int(float(week_recommend[:-1]) * 10000) if week_recommend[-1] == '万' else int(week_recommend)

            # 将数据插入到 MySQL 数据库中
            try:
                insert_sql = """
                             INSERT INTO publish_book (img, name, author, up_time, up_chapter, category, wordcount, \
                                                       all_recommend, week_recommend, introduction, chapters) \
                             VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) \
                             """
                cursor.execute(insert_sql, (
                    img, name, author[3:], up_time[5:], up_chapter[5:], category, wordcount, all_recommend,
                    week_recommend, introduction, int(chapters[3:-1])
                ))
                conn.commit()
                print(f"成功爬取数据：{name}")
            except Exception as e:
                print(f"爬取数据失败：{e}")
                conn.rollback()  # 回滚事务，避免脏数据

            # 关闭详情页，切回列表页
            driver.close()
            driver.switch_to.window(original_window)
            time.sleep(1)

            # 每处理完一个详情页，更新进度状态
            state = {
                'cate_idx': cate_idx,
                'page': page,
                'item_rid': rid + 1,    # 下一个要处理的详情页
                'cate_url': cate_url
            }
            save_state(state)

        # 更新状态为下一页开始
        state = {
            'cate_idx': cate_idx,
            'page': page + 1,   # 下一个要处理的页码
            'item_rid': 1,
            'cate_url': cate_url
        }
        save_state(state)

    # 更新状态为下一类别开始
    state = {
        'cate_idx': cate_idx + 1,   # 下一个要处理的类别
        'page': 1,
        'item_rid': 1,
        'cate_url': ''
    }
    save_state(state)

# 释放资源
driver.quit()
cursor.close()
conn.close()
print('浏览器和数据库连接已关闭。')

# 全部完成
print('所有数据爬取完成！')
