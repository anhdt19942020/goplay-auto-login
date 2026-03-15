#!/bin/bash
# GoPlay API Service Manager
# Usage: ./manage.sh [start|stop|restart|status|logs|update|reset]

SERVICE="goplay-api"
APP_DIR="/opt/goplay-auto-login"

case "$1" in
  start)
    systemctl start $SERVICE
    echo "✅ Started"
    ;;
  stop)
    systemctl stop $SERVICE
    echo "⏹ Stopped"
    ;;
  restart)
    systemctl restart $SERVICE
    echo "🔄 Restarted"
    ;;
  status)
    systemctl status $SERVICE --no-pager
    ;;
  logs)
    journalctl -u $SERVICE -f --no-pager -n ${2:-50}
    ;;
  update)
    cd $APP_DIR
    git pull
    systemctl restart $SERVICE
    echo "✅ Updated & restarted"
    ;;
  reset)
    echo "🔄 Full reset: stop service, kill Chrome, clean profile, restart..."
    systemctl stop $SERVICE
    pkill -f chrome 2>/dev/null
    pkill -f Xvfb 2>/dev/null
    rm -rf $APP_DIR/chrome_profile_vlcm/*
    rm -rf $APP_DIR/debug/*
    sleep 1
    systemctl start $SERVICE
    echo "✅ Reset complete"
    ;;
  *)
    echo "GoPlay API Manager"
    echo "Usage: $0 {start|stop|restart|status|logs|update|reset}"
    echo ""
    echo "  start    Start service"
    echo "  stop     Stop service"
    echo "  restart  Restart service"
    echo "  status   Show service status"
    echo "  logs     Tail logs (logs 100 = last 100 lines)"
    echo "  update   Git pull + restart"
    echo "  reset    Full reset: kill Chrome, clean profile, restart"
    ;;
esac
