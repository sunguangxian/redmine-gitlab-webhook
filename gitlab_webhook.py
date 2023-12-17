from flask import Flask, request
from redminelib import Redmine

app = Flask(__name__)

# 配置Redmine的URL
REDMINE_URL = 'http://192.168.1.208:3000'
# 映射表，将GitLab用户与对应的Redmine用户的API密钥关联起来
USER_API_KEY_MAPPING = {
    'sunguangxian': '8f897735602fae9fd600c04fe387a1e6e8c22fb4',
    # 添加更多的映射...
}


def extract_issue_id(commit_message):
    # 支持 "fix #123", "close #456", "修复 #789", "解决 #101" 等关键字格式
    keywords = ["fix", "close", "修复", "解决"]
    
    for keyword in keywords:
        keyword_with_space = f"{keyword} redmine-#"
        index = commit_message.lower().find(keyword_with_space)
        if index != -1:
            return commit_message[index + len(keyword_with_space):].split()[0]

    return None

def update_redmine_issue_status(issue_id, status_id, redmine):
    try:
        issue = redmine.issue.get(issue_id)

        # 如果问题的状态已经是目标状态，不进行状态修改
        if issue.status.id == status_id:
            print(f"Redmine issue {issue_id} is already in status {status_id}")
            return "No status change. Issue is already in the specified status."

        redmine.issue.update(
                issue_id,
                status_id = status_id,
                done_ratio = 100,
            )

        print(f"Updated Redmine issue {issue_id} status to {status_id}")
        return f"Successfully updated Redmine issue {issue_id} status to {status_id}"
    except Exception as e:
        error_message = f"Error updating Redmine issue {issue_id} status: {str(e)}"
        print(error_message)
        return error_message

def add_comment_to_redmine_issue(issue_id, comment, redmine):
    try:
        # 更新注释和其他字段
        redmine.issue.update(issue_id,
            notes=comment,
            # 其他字段按照需要添加
        )

        print(f"Added comment to Redmine issue {issue_id}: {comment}")
    except Exception as e:
        print(f"Error adding comment to Redmine issue {issue_id}: {str(e)}")

def update_redmine_user_field(issue_id, user_name, redmine):
    try:
        issue = redmine.issue.get(issue_id)
        custom_field_id = get_custom_field_id(issue, 'GitLab User')  # 替换为你的自定义字段名称
        if custom_field_id:
            # 使用 update 方法更新 'GitLab User' 字段
            redmine.issue.update(
                issue_id,
                custom_fields=[{'id': custom_field_id, 'value': user_name}],
            )
            print(f"Updated Redmine issue {issue_id} with GitLab User: {user_name}")
        else:
            print(f"Custom field 'GitLab User' not found in Redmine.")
    except Exception as e:
        print(f"Error updating GitLab User field for Redmine issue {issue_id}: {str(e)}")

def get_custom_field_id(issue, field_name):
    # 获取Redmine中自定义字段的ID
    for custom_field in issue.custom_fields:
        if custom_field.name == field_name:
            return custom_field.id
    return None


@app.route('/', methods=['POST'])
def gitlab_webhook():
    data = request.get_json()

    # 打印完整的 Webhook 数据
    #print("Received GitLab Webhook:")
    #print(data)

    # 检查事件类型是否是Push事件
    if 'object_kind' in data and data['object_kind'] == 'push':
        commits = data.get('commits', [])
        user_name = data.get('user_username', 'Unknown User')

        # 获取用户对应的Redmine API密钥
        redmine_api_key = USER_API_KEY_MAPPING.get(user_name)

        if redmine_api_key:
            redmine = Redmine(REDMINE_URL, key=redmine_api_key)

            for commit in commits:
                author_name = commit.get('author', {}).get('name', 'Unknown Author')
                commit_message = commit.get('message', 'No commit message')
                commit_id = commit.get('id', 'No commit ID')

                # 获取提交信息中的问题ID
                issue_id = extract_issue_id(commit_message)

                if issue_id:

                    # 获取项目的问题状态列表
                    statuses = redmine.issue_status.all()
                    # 遍历状态列表并找到状态为已解决的ID
                    resolved_status_id = None
                    for status in statuses:
                        # 如果状态名称为"已解决"，保存其ID并退出循环
                        if status.name == '已解决':
                            resolved_status_id = status.id
                            break

                    # 修改Redmine上对应问题的状态为已完成
                    status_update_result = update_redmine_issue_status(issue_id, resolved_status_id, redmine)

                    # 只有在状态更新成功时才执行以下操作
                    if "Successfully updated" in status_update_result:
                        # 在Redmine上添加注释，提交信息
                        add_comment_to_redmine_issue(issue_id, f"Commit by {author_name} ({commit_id}): {commit_message}", redmine)
        
                        # 将GitLab用户信息写入Redmine自定义字段
                        update_redmine_user_field(issue_id, user_name, redmine)
                    else:
                        print("Skipping additional operations as the issue status did not change.")


    return 'Webhook received succ!', 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)

