# redmine-gitlab-webhook

- 基于Flask运行的py脚本，实现gitlab提交改动时可以同步修改redmine问题状态，并同步提交信息到redmine对应问题
- 需要手动建立gitlab用户及redmine用户对应关系，使用gitlab用户名及redmine用户对应的api做对应
- gitlab需要新建系统钩子，绑定该脚本对应的地址
