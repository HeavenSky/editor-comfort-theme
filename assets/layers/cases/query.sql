-- 每日汇总
SELECT u.id, u.name, COUNT(o.id) AS orders, SUM(o.amount) AS total
FROM users u
LEFT JOIN orders o ON o.user_id = u.id AND o.status = 'paid'
WHERE u.created_at >= '2026-01-01' AND u.deleted IS NULL
GROUP BY u.id, u.name
HAVING COUNT(o.id) > 5
ORDER BY total DESC
LIMIT 100;
