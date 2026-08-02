# Spring 事务与生产化

## 事务边界

Spring 提供跨 JDBC、JPA、Hibernate 等技术的一致事务抽象，支持声明式与编程式事务。声明式事务通常由代理拦截方法调用，因此同一对象内部自调用可能绕过代理。回滚规则、传播行为、隔离级别和事务边界必须结合数据库行为理解。

事务不能自动覆盖远程 HTTP、消息发布等外部副作用。跨资源一致性可根据业务选择 Outbox、幂等消费、补偿或分布式事务。长事务会延长锁持有时间并消耗连接，应避免把慢远程调用放进数据库事务。

### 面试题：`@Transactional` 为什么可能不生效？

参考答案要点：代理未生效、自调用、方法可见性或配置问题、异常被吞掉、回滚规则不匹配、使用错误事务管理器；通过事务日志、集成测试和数据库状态验证。

## 生产可观测性

Spring Boot Actuator 可暴露健康、指标和管理能力。Liveness 表示应用自身是否还能恢复；Readiness 表示是否准备接收流量。Liveness 不宜依赖外部数据库健康，否则外部故障可能引起实例集体重启。

### 面试题：如何设计 Java 服务健康检查？

参考答案要点：区分存活与就绪；就绪可反映必要依赖和过载状态；端点需要鉴权与最小暴露；结合指标、日志和 Trace，而不是只看 HTTP 200。

来源：https://docs.spring.io/spring-framework/reference/data-access/transaction.html 、https://docs.spring.io/spring-boot/reference/features/spring-application.html
