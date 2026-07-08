"""
数据库层 - SQLite 操作封装
"""
import sqlite3
import os
import sys
from datetime import datetime

# 数据目录：exe 同目录 / 源码同目录
if getattr(sys, 'frozen', False):
    _APP_DIR = os.path.dirname(sys.executable)
else:
    _APP_DIR = os.path.dirname(os.path.abspath(__file__))

DB_DIR = os.path.join(_APP_DIR, "data")
DB_PATH = os.path.join(DB_DIR, "prompts.db")


def get_db_path():
    os.makedirs(DB_DIR, exist_ok=True)
    return DB_PATH


def get_connection():
    conn = sqlite3.connect(get_db_path())
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
    conn = get_connection()
    c = conn.cursor()

    # 分类表
    c.execute("""
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            sort_order INTEGER DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now','localtime'))
        )
    """)

    # 标签表
    c.execute("""
        CREATE TABLE IF NOT EXISTS tags (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            sort_order INTEGER DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now','localtime'))
        )
    """)

    # 背景色表
    c.execute("""
        CREATE TABLE IF NOT EXISTS colors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            hex_value TEXT NOT NULL,
            sort_order INTEGER DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now','localtime'))
        )
    """)

    # 提示词表
    c.execute("""
        CREATE TABLE IF NOT EXISTS prompts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            content TEXT DEFAULT '',
            category_id INTEGER,
            color_id INTEGER,
            sort_order INTEGER DEFAULT 0,
            is_pinned INTEGER DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now','localtime')),
            updated_at TEXT DEFAULT (datetime('now','localtime')),
            FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE SET NULL,
            FOREIGN KEY (color_id) REFERENCES colors(id) ON DELETE SET NULL
        )
    """)

    # 提示词-标签关联表
    c.execute("""
        CREATE TABLE IF NOT EXISTS prompt_tags (
            prompt_id INTEGER NOT NULL,
            tag_id INTEGER NOT NULL,
            PRIMARY KEY (prompt_id, tag_id),
            FOREIGN KEY (prompt_id) REFERENCES prompts(id) ON DELETE CASCADE,
            FOREIGN KEY (tag_id) REFERENCES tags(id) ON DELETE CASCADE
        )
    """)

    # 导航链接表
    c.execute("""
        CREATE TABLE IF NOT EXISTS navigation (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            url TEXT NOT NULL,
            sort_order INTEGER DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now','localtime'))
        )
    """)

    # 设置表
    c.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    """)

    # 预设数据
    _insert_presets(c)

    conn.commit()
    conn.close()


def _insert_presets(c):
    # 预设分类
    default_cats = [
        ("编程", 0), ("写作", 1), ("营销", 2), ("设计", 3),
        ("教育", 4), ("生活", 5), ("商业", 6), ("其他", 7),
    ]
    for name, order in default_cats:
        c.execute(
            "INSERT OR IGNORE INTO categories (name, sort_order) VALUES (?, ?)",
            (name, order)
        )

    # 预设标签
    default_tags = [
        ("Python", 0), ("JavaScript", 1), ("React", 2),
        ("文案", 3), ("SEO", 4), ("小说", 5),
    ]
    for name, order in default_tags:
        c.execute(
            "INSERT OR IGNORE INTO tags (name, sort_order) VALUES (?, ?)",
            (name, order)
        )

    # 预设背景色
    default_colors = [
        ("重要-红", "#FFCDD2", 0),
        ("待处理-黄", "#FFF9C4", 1),
        ("完成-绿", "#C8E6C9", 2),
        ("信息-蓝", "#BBDEFB", 3),
        ("草稿-灰", "#E0E0E0", 4),
    ]
    for name, hex_val, order in default_colors:
        c.execute(
            "INSERT OR IGNORE INTO colors (name, hex_value, sort_order) VALUES (?, ?, ?)",
            (name, hex_val, order)
        )

    # 预设导航
    default_nav = [
        ("ChatGPT", "https://chat.openai.com", 0),
        ("DeepSeek", "https://chat.deepseek.com", 1),
        ("Claude", "https://claude.ai", 2),
        ("通义千问", "https://tongyi.aliyun.com", 3),
        ("文心一言", "https://yiyan.baidu.com", 4),
        ("Kimi", "https://kimi.moonshot.cn", 5),
    ]
    for name, url, order in default_nav:
        c.execute(
            "INSERT OR IGNORE INTO navigation (name, url, sort_order) VALUES (?, ?, ?)",
            (name, url, order)
        )


# ============ CRUD: Categories ============
def get_categories():
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM categories ORDER BY sort_order, id"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def add_category(name):
    conn = get_connection()
    try:
        cur = conn.execute(
            "INSERT INTO categories (name) VALUES (?)", (name,)
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def rename_category(cat_id, new_name):
    conn = get_connection()
    conn.execute("UPDATE categories SET name=? WHERE id=?", (new_name, cat_id))
    conn.commit()
    conn.close()


def delete_category(cat_id):
    conn = get_connection()
    conn.execute("DELETE FROM categories WHERE id=?", (cat_id,))
    conn.commit()
    conn.close()


# ============ CRUD: Tags ============
def get_tags():
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM tags ORDER BY sort_order, id"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def add_tag(name):
    conn = get_connection()
    try:
        cur = conn.execute("INSERT INTO tags (name) VALUES (?)", (name,))
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def rename_tag(tag_id, new_name):
    conn = get_connection()
    conn.execute("UPDATE tags SET name=? WHERE id=?", (new_name, tag_id))
    conn.commit()
    conn.close()


def delete_tag(tag_id):
    conn = get_connection()
    conn.execute("DELETE FROM tags WHERE id=?", (tag_id,))
    conn.commit()
    conn.close()


# ============ CRUD: Colors ============
def get_colors():
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM colors ORDER BY sort_order, id"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def add_color(name, hex_value):
    conn = get_connection()
    try:
        cur = conn.execute(
            "INSERT INTO colors (name, hex_value) VALUES (?, ?)",
            (name, hex_value)
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def rename_color(color_id, new_name):
    conn = get_connection()
    conn.execute("UPDATE colors SET name=? WHERE id=?", (new_name, color_id))
    conn.commit()
    conn.close()


def delete_color(color_id):
    conn = get_connection()
    conn.execute("DELETE FROM colors WHERE id=?", (color_id,))
    conn.commit()
    conn.close()


# ============ CRUD: Prompts ============
def get_prompts(category_id=None, tag_id=None, color_id=None, search=None):
    """获取提示词列表，支持多条件筛选"""
    conn = get_connection()
    query = "SELECT DISTINCT p.* FROM prompts p"
    where = []
    params = []

    if tag_id is not None and tag_id > 0:
        query += " JOIN prompt_tags pt ON p.id = pt.prompt_id"
        where.append("pt.tag_id = ?")
        params.append(tag_id)
    # tag_id == 0 means "无标签"
    elif tag_id == 0:
        query += " LEFT JOIN prompt_tags pt ON p.id = pt.prompt_id"
        where.append("pt.tag_id IS NULL")

    if category_id is not None:
        if category_id == -1:
            where.append("p.category_id IS NULL")
        else:
            where.append("p.category_id = ?")
            params.append(category_id)

    if color_id is not None:
        if color_id == -1:
            where.append("p.color_id IS NULL")
        else:
            where.append("p.color_id = ?")
            params.append(color_id)

    if search:
        where.append("(p.title LIKE ? OR p.content LIKE ?)")
        kw = f"%{search}%"
        params.extend([kw, kw])

    if where:
        query += " WHERE " + " AND ".join(where)

    query += " ORDER BY p.is_pinned DESC, p.sort_order, p.id"

    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_prompt(prompt_id):
    conn = get_connection()
    row = conn.execute("SELECT * FROM prompts WHERE id=?", (prompt_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def get_prompt_tags(prompt_id):
    conn = get_connection()
    rows = conn.execute(
        """SELECT t.* FROM tags t
           JOIN prompt_tags pt ON t.id = pt.tag_id
           WHERE pt.prompt_id = ?
           ORDER BY t.sort_order, t.id""",
        (prompt_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def add_prompt(title, content="", category_id=None, color_id=None):
    conn = get_connection()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    # 获取当前分类下的最大排序号
    max_order = conn.execute(
        "SELECT COALESCE(MAX(sort_order), 0) FROM prompts"
    ).fetchone()[0]
    cur = conn.execute(
        """INSERT INTO prompts (title, content, category_id, color_id, sort_order, created_at, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (title, content, category_id, color_id, max_order + 1, now, now)
    )
    conn.commit()
    prompt_id = cur.lastrowid
    conn.close()
    return prompt_id


def update_prompt(prompt_id, title=None, content=None, category_id=None, color_id=None):
    conn = get_connection()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    fields = ["updated_at=?"]
    params = [now]

    if title is not None:
        fields.append("title=?")
        params.append(title)
    if content is not None:
        fields.append("content=?")
        params.append(content)
    if category_id is not None:
        fields.append("category_id=?")
        params.append(category_id)
    if color_id is not None:
        fields.append("color_id=?")
        params.append(color_id)

    params.append(prompt_id)
    conn.execute(
        f"UPDATE prompts SET {', '.join(fields)} WHERE id=?",
        params
    )
    conn.commit()
    conn.close()


def delete_prompt(prompt_id):
    conn = get_connection()
    conn.execute("DELETE FROM prompts WHERE id=?", (prompt_id,))
    conn.commit()
    conn.close()


def toggle_pin_prompt(prompt_id):
    """切换置顶状态"""
    conn = get_connection()
    row = conn.execute(
        "SELECT is_pinned FROM prompts WHERE id=?", (prompt_id,)
    ).fetchone()
    if row:
        new_val = 0 if row[0] else 1
        conn.execute(
            "UPDATE prompts SET is_pinned=? WHERE id=?", (new_val, prompt_id)
        )
        conn.commit()
    conn.close()


def move_prompt_to_category(prompt_id, category_id):
    """移动提示词到指定分类"""
    conn = get_connection()
    conn.execute(
        "UPDATE prompts SET category_id=?, updated_at=datetime('now','localtime') WHERE id=?",
        (category_id, prompt_id)
    )
    conn.commit()
    conn.close()


def set_prompt_tags(prompt_id, tag_ids):
    """设置提示词的标签列表"""
    conn = get_connection()
    conn.execute("DELETE FROM prompt_tags WHERE prompt_id=?", (prompt_id,))
    for tid in tag_ids:
        conn.execute(
            "INSERT OR IGNORE INTO prompt_tags (prompt_id, tag_id) VALUES (?, ?)",
            (prompt_id, tid)
        )
    conn.commit()
    conn.close()


def update_prompt_sort_order(prompt_id, sort_order):
    conn = get_connection()
    conn.execute(
        "UPDATE prompts SET sort_order=?, updated_at=datetime('now','localtime') WHERE id=?",
        (sort_order, prompt_id)
    )
    conn.commit()
    conn.close()


def batch_update_sort_orders(order_map):
    """批量更新排序顺序 {prompt_id: sort_order}"""
    conn = get_connection()
    for pid, order in order_map.items():
        conn.execute(
            "UPDATE prompts SET sort_order=?, updated_at=datetime('now','localtime') WHERE id=?",
            (order, pid)
        )
    conn.commit()
    conn.close()


def batch_delete_prompts(prompt_ids):
    conn = get_connection()
    for pid in prompt_ids:
        conn.execute("DELETE FROM prompts WHERE id=?", (pid,))
    conn.commit()
    conn.close()


def batch_move_prompts(prompt_ids, category_id):
    conn = get_connection()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    for pid in prompt_ids:
        conn.execute(
            "UPDATE prompts SET category_id=?, updated_at=? WHERE id=?",
            (category_id, now, pid)
        )
    conn.commit()
    conn.close()


def batch_set_color(prompt_ids, color_id):
    conn = get_connection()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    for pid in prompt_ids:
        conn.execute(
            "UPDATE prompts SET color_id=?, updated_at=? WHERE id=?",
            (color_id, now, pid)
        )
    conn.commit()
    conn.close()


def batch_set_tags(prompt_ids, tag_ids):
    """批量设置标签"""
    conn = get_connection()
    for pid in prompt_ids:
        conn.execute("DELETE FROM prompt_tags WHERE prompt_id=?", (pid,))
        for tid in tag_ids:
            conn.execute(
                "INSERT OR IGNORE INTO prompt_tags (prompt_id, tag_id) VALUES (?, ?)",
                (pid, tid)
            )
    conn.commit()
    conn.close()


# ============ Navigation ============
def get_navigation():
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM navigation ORDER BY sort_order, id"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def add_navigation(name, url):
    conn = get_connection()
    max_order = conn.execute(
        "SELECT COALESCE(MAX(sort_order), 0) FROM navigation"
    ).fetchone()[0]
    conn.execute(
        "INSERT INTO navigation (name, url, sort_order) VALUES (?, ?, ?)",
        (name, url, max_order + 1)
    )
    conn.commit()
    conn.close()


def update_navigation(nav_id, name, url):
    conn = get_connection()
    conn.execute(
        "UPDATE navigation SET name=?, url=? WHERE id=?",
        (name, url, nav_id)
    )
    conn.commit()
    conn.close()


def delete_navigation(nav_id):
    conn = get_connection()
    conn.execute("DELETE FROM navigation WHERE id=?", (nav_id,))
    conn.commit()
    conn.close()


def update_nav_sort_order(nav_id, sort_order):
    conn = get_connection()
    conn.execute(
        "UPDATE navigation SET sort_order=? WHERE id=?",
        (sort_order, nav_id)
    )
    conn.commit()
    conn.close()


# ============ Settings ============
def get_setting(key, default=None):
    conn = get_connection()
    row = conn.execute(
        "SELECT value FROM settings WHERE key=?", (key,)
    ).fetchone()
    conn.close()
    return row[0] if row else default


def set_setting(key, value):
    conn = get_connection()
    conn.execute(
        "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
        (key, value)
    )
    conn.commit()
    conn.close()


# ============ Import / Export ============
def export_prompts_csv(prompt_ids, filepath):
    """导出选中提示词为 CSV"""
    import csv
    conn = get_connection()
    placeholders = ','.join('?' * len(prompt_ids))
    rows = conn.execute(
        f"""SELECT p.title, p.content, c.name as category,
                   GROUP_CONCAT(t.name, ',') as tags
            FROM prompts p
            LEFT JOIN categories c ON p.category_id = c.id
            LEFT JOIN prompt_tags pt ON p.id = pt.prompt_id
            LEFT JOIN tags t ON pt.tag_id = t.id
            WHERE p.id IN ({placeholders})
            GROUP BY p.id""",
        prompt_ids
    ).fetchall()
    conn.close()

    with open(filepath, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f)
        writer.writerow(['标题', '正文', '分类', '标签'])
        for row in rows:
            writer.writerow([row['title'], row['content'], row['category'] or '', row['tags'] or ''])
    return True


def export_all_csv(filepath):
    """导出全部提示词为 CSV"""
    conn = get_connection()
    rows = conn.execute(
        """SELECT p.title, p.content, c.name as category,
                  GROUP_CONCAT(t.name, ',') as tags
           FROM prompts p
           LEFT JOIN categories c ON p.category_id = c.id
           LEFT JOIN prompt_tags pt ON p.id = pt.prompt_id
           LEFT JOIN tags t ON pt.tag_id = t.id
           GROUP BY p.id"""
    ).fetchall()
    conn.close()

    import csv
    with open(filepath, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f)
        writer.writerow(['标题', '正文', '分类', '标签'])
        for row in rows:
            writer.writerow([row['title'], row['content'], row['category'] or '', row['tags'] or ''])
    return True


def import_prompts_csv(filepath):
    """从 CSV 导入提示词"""
    import csv
    imported = 0
    conn = get_connection()

    with open(filepath, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            title = row.get('标题', '').strip()
            content = row.get('正文', '').strip()
            cat_name = row.get('分类', '').strip()
            tag_names = [t.strip() for t in row.get('标签', '').split(',') if t.strip()]

            if not title:
                continue

            # 查找或创建分类
            cat_id = None
            if cat_name:
                cat = conn.execute(
                    "SELECT id FROM categories WHERE name=?", (cat_name,)
                ).fetchone()
                if cat:
                    cat_id = cat[0]
                else:
                    cur = conn.execute(
                        "INSERT INTO categories (name) VALUES (?)", (cat_name,)
                    )
                    cat_id = cur.lastrowid

            # 插入提示词
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            max_order = conn.execute(
                "SELECT COALESCE(MAX(sort_order), 0) FROM prompts"
            ).fetchone()[0]
            cur = conn.execute(
                """INSERT INTO prompts (title, content, category_id, sort_order, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (title, content, cat_id, max_order + imported + 1, now, now)
            )
            prompt_id = cur.lastrowid

            # 处理标签
            for tname in tag_names:
                tag = conn.execute(
                    "SELECT id FROM tags WHERE name=?", (tname,)
                ).fetchone()
                if not tag:
                    tag_cur = conn.execute(
                        "INSERT INTO tags (name) VALUES (?)", (tname,)
                    )
                    tag_id = tag_cur.lastrowid
                else:
                    tag_id = tag[0]
                conn.execute(
                    "INSERT OR IGNORE INTO prompt_tags (prompt_id, tag_id) VALUES (?, ?)",
                    (prompt_id, tag_id)
                )

            imported += 1

    conn.commit()
    conn.close()
    return imported
