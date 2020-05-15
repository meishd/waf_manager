CREATE TABLE `ip_blacklist` (
  `id` bigint(11) NOT NULL AUTO_INCREMENT,
  `ip_addr` varchar(15) COLLATE utf8mb4_bin DEFAULT NULL,
  `status` int(11) DEFAULT '0' COMMENT '0: valid 有效, 1: invalid 失效',
  `effective_time` int(11) DEFAULT '10' COMMENT '有效期，单位：分钟',
  `create_time` datetime DEFAULT CURRENT_TIMESTAMP,
  `modify_time` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `source_type` enum('手动','api','spark') COLLATE utf8mb4_bin DEFAULT NULL,
  `source` varchar(255) COLLATE utf8mb4_bin DEFAULT NULL COMMENT '黑名单来源',
  `remark` varchar(255) COLLATE utf8mb4_bin DEFAULT NULL COMMENT '备注',
  PRIMARY KEY (`id`),
  UNIQUE KEY `idx_ipbl_ip` (`ip_addr`)
);

CREATE trigger trig_ipblacklist_ip_insert 
before insert on ip_blacklist for each row
begin 
    declare msg varchar(255);
    if (new.ip_addr regexp '^[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}$' = 0) then 
        set msg = 'invalid ip format';
        signal sqlstate 'LB001' set message_text = msg;
    end if;
    if (new.ip_addr like '10.%' 
        or new.ip_addr = '218.94.158.227') then
        set msg = 'ip forbidden';
        signal sqlstate 'LB002' set message_text = msg;
    end if;

end;

CREATE trigger trig_ipblacklist_ip_update
before update on ip_blacklist for each row
begin 
    declare msg varchar(255);
    if (new.ip_addr regexp '^[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}$' = 0) then 
        set msg = 'invalid ip format';
        signal sqlstate 'LB001' set message_text = msg;
    end if;
    if (new.ip_addr like '10.%' 
        or new.ip_addr = '218.94.158.227') then
        set msg = 'ip forbidden';
        signal sqlstate 'LB002' set message_text = msg;
    end if;
end;

CREATE TABLE `ip_white` (
  `id` bigint(11) NOT NULL AUTO_INCREMENT,
  `ip_addr` varchar(15) COLLATE utf8mb4_bin NOT NULL,
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `user_name` varchar(100) COLLATE utf8mb4_bin NOT NULL,
  `remark` varchar(255) COLLATE utf8mb4_bin DEFAULT NULL COMMENT '备注',
  PRIMARY KEY (`id`)
);

CREATE TABLE `job_process` (
  `id` int(11) NOT NULL,
  `id_deal_until` bigint(20) DEFAULT NULL,
  PRIMARY KEY (`id`)
);

insert into job_process values(1,0);

CREATE TABLE `match_record` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `rule_id` int(11) NOT NULL,
  `ip_addr` varchar(15) COLLATE utf8mb4_bin NOT NULL,
  `win_begin` datetime NOT NULL,
  `win_end` datetime NOT NULL,
  `request_cnt` bigint(20) NOT NULL,
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_mr_createtime` (`create_time`)
);

CREATE TABLE `rule` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `domain` varchar(60) COLLATE utf8mb4_bin NOT NULL,
  `url` varchar(150) COLLATE utf8mb4_bin NOT NULL,
  `match_type` enum('prefix','exact') COLLATE utf8mb4_bin NOT NULL,
  `win_duration` int(11) NOT NULL,
  `slide_duration` int(11) NOT NULL,
  `req_threshold` int(11) NOT NULL,
  `active_status` int(11) NOT NULL DEFAULT '0',
  `block_duration` int(11) DEFAULT NULL,
  `create_time` datetime DEFAULT CURRENT_TIMESTAMP,
  `user_name` varchar(100) COLLATE utf8mb4_bin DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uidx_rule_domain_url` (`domain`,`url`)
);

CREATE TABLE `user_base` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `user_name` varchar(30) COLLATE utf8mb4_bin NOT NULL,
  `password` varchar(100) COLLATE utf8mb4_bin NOT NULL,
  `active` int(11) NOT NULL,
  `priv_rule` int(11) DEFAULT NULL,
  `login_cnt` bigint(20) NOT NULL DEFAULT '0',
  `update_time` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `idx_ub_username` (`user_name`)
);

-- 初始化用户，密码：123456，无规则操作的权限
-- 产生密码：
-- from werkzeug.security import generate_password_hash
-- generate_password_hash('123456')
insert into user_base(user_name,password,active,priv_rule)
values ('zhangsan','pbkdf2:sha256:150000$1XACc3wp$557099e35d9d75be44ce9e19c0e51bffb1f14bb8bfab77881a3b2519a350899e',0,1);




CREATE PROCEDURE `proc_spark_ipblacklist`()
BEGIN
    declare v_auto_ip_quota int default 1000;      -- 支持最大自动拉黑IP数
    declare v_id_last bigint;                      -- 上次处理到的id(含)
    declare v_id_curr bigint;                      -- 当前id
    declare v_ip_blacklist_cnt int;                -- 现有的拉黑IP数
    declare v_to_add bigint;                       -- 当前新增拉黑IP数

    select id_deal_until into v_id_last from job_process where id=1;
    select max(id) into v_id_curr from match_record;
    select count(*) into v_ip_blacklist_cnt from ip_blacklist where source_type='spark';

    start transaction;
    -- 当前有新增IP
    if (v_id_curr > v_id_last) then 
        -- 当前新增需要处理的IP数
        select count(distinct rule_id,real_ip) into v_to_add
        from match_record t
        where id > v_id_last
        and id <= v_id_curr
        and real_ip not in (select ip_addr from ip_blacklist);

        -- 新增数量大于配额，直接清空所有存量IP黑名单
        if (v_to_add >= v_auto_ip_quota) then 
            delete from ip_blacklist where source_type='spark';
        -- 新增数量与存量IP黑名单之和大于配额，删除存量IP黑名单中老的IP
        elseif (v_to_add + v_ip_blacklist_cnt > v_auto_ip_quota) then 
            select v_to_add + v_ip_blacklist_cnt - v_auto_ip_quota into @v_to_delete; 
            prepare s1 from "delete from ip_blacklist where source_type='spark' order by create_time limit ?";
            execute s1 using @v_to_delete;
        end if;
        -- 插入新增IP
        insert into ip_blacklist(source,ip_addr,effective_time,status,source_type)
				select distinct concat('rule',rule_id),real_ip,
							(select block_duration from rule where id=t.rule_id), 0,'spark'
				from match_record t
				where id > v_id_last
				and id <= v_id_curr
				and real_ip not in (select ip_addr from ip_blacklist)
				limit 1000;

        update job_process set id_deal_until = v_id_curr where id = 1;
    end if;
    commit;    

end;

delimiter $$
CREATE EVENT `job_spark_ipblacklist` ON SCHEDULE EVERY 3 SECOND STARTS now() ON COMPLETION PRESERVE ENABLE DO 
begin
  declare continue handler for sqlexception begin end;
	if get_lock('job_spark_ipblacklist', 0) THEN 
			call proc_spark_ipblacklist;
	end if;
	do release_lock('job_spark_ipblacklist');
end $$
delimiter ;



CREATE PROCEDURE `proc_ip_blacklist_status_update`()
begin 
    update ip_blacklist
    set status=1
    where date_add(modify_time,INTERVAL effective_time minute) < now();
    commit;

    delete from ip_blacklist
    where status = 1
    and modify_time < DATE_SUB(now(),INTERVAL 1 day); 
    commit;
end;


CREATE EVENT `job_ip_blacklist_status_update` ON SCHEDULE EVERY 1 MINUTE STARTS now() ON COMPLETION PRESERVE ENABLE DO 
call proc_ip_blacklist_status_update();
