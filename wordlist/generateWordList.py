import itertools
 
print("generate pwd start")
# 密码包含这些字符,如果需要生成的密码包含其他字符串,直接更改这个key
key = '0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ!@#$%^*()' 
# repeat为生成密码重复次数,即密码字典中密码的字符串长度
passwords = itertools.product(key, repeat=10)
f = open('wordlist.txt', 'a')
for i in passwords:
    f.write("".join(i))
    f.write('\n')
print("generate pwd finished")
f.close()



