# Meta Load Balancer

یک سیستم هوشمند برای مدیریت بار ترافیک با استفاده از یادگیری ماشین که به صورت خودکار الگوریتم load balancing را بر اساس متریک‌های سیستم تغییر می‌دهد.

## معماری سیستم

- **سرویس‌های Node.js (svc1, svc2, svc3)**: سه میکروسرویس ساده که هر کدام یک JSON با نام سرویس و timestamp برمی‌گردانند.
- **Nginx**: به عنوان load balancer اصلی که ترافیک را بین سرویس‌ها توزیع می‌کند.
- **Meta-Load-Balancer**: سرویس هوشمند Python که با استفاده از یادگیری ماشین، الگوریتم مناسب load balancing را انتخاب می‌کند.
- **Prometheus**: برای جمع‌آوری متریک‌های سیستم.
- **Grafana**: برای نمایش متریک‌ها و وضعیت سیستم.
- **Locust**: برای شبیه‌سازی ترافیک و تست سیستم.

## نحوه اجرا

```bash
git clone https://github.com/mohammadha98/meta-load-balancer.git
cd meta-load-balancer
docker-compose up --build
```

## دسترسی به سرویس‌ها

- **وب‌سایت اصلی**: http://localhost:80
- **Grafana**: http://localhost:3000 (نام کاربری: admin، رمز عبور: admin)
- **Prometheus**: http://localhost:9090
- **Locust UI**: http://localhost:8089

## نحوه کار

1. سرویس Meta-Load-Balancer هر 5 ثانیه متریک‌های سیستم را از Prometheus می‌خواند.
2. با استفاده از مدل ML، الگوریتم مناسب load balancing را پیش‌بینی می‌کند.
3. فایل `algo.conf` را آپدیت کرده و Nginx را reload می‌کند.
4. الگوریتم‌های پشتیبانی شده: round-robin، least_conn و ip_hash.

## داشبورد Grafana

داشبورد Grafana شامل پنل‌های زیر است:
- CPU و Memory از node-exporter
- HTTP latency و throughput از Prometheus
- نمایشگر الگوریتم فعلی load balancing