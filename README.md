# GLOW Railway-Optimized Backend

Complete dating application backend with Magic 10 compatibility matching, Human Design integration, and admin console. Optimized for Railway deployment with single-file architecture.

## 🌟 Features

### Core Features
- **Magic 10 Matching System** - 10-dimensional compatibility algorithm
- **User Authentication** - Registration, login, session management
- **Admin Console** - User management, status updates, system monitoring
- **Human Design Integration** - Birth chart calculations via external API
- **Email Notifications** - Welcome emails, match notifications via Mailgun

### Technical Features
- **Railway-Optimized** - Single-file architecture, lazy database initialization
- **PostgreSQL Database** - 8 tables with optimized schema
- **RESTful API** - 25+ endpoints with comprehensive error handling
- **CORS Support** - Frontend integration ready
- **Health Monitoring** - System status and debugging endpoints

## 🚂 Railway Deployment

### Prerequisites
1. Railway account
2. GitHub repository
3. Environment variables configured

### Environment Variables

#### Required
```
SECRET_KEY=your-secure-secret-key-here
```

#### Optional (External Services)
```
# Mailgun Email Service
MAILGUN_API_KEY=key-your-mailgun-api-key
MAILGUN_DOMAIN=your-domain.mailgun.org
MAILGUN_BASE_URL=https://api.mailgun.net/v3
FROM_EMAIL=noreply@yourdomain.com

# Human Design API
HD_API_KEY=your-human-design-api-key
GEO_API_KEY=your-google-places-api-key
HD_API_BASE_URL=https://api.humandesignapi.nl/v1

# Frontend Integration
FRONTEND_URL=https://your-frontend.vercel.app
CORS_ORIGINS=https://your-frontend.vercel.app,http://localhost:3000
```

### Deployment Steps

1. **Create Railway Project**
   ```bash
   # Create empty Railway project
   # Add PostgreSQL service first
   # Add web service from GitHub repository
   ```

2. **Configure Environment Variables**
   - Set `SECRET_KEY` in Railway dashboard
   - Add optional API keys as needed
   - Railway auto-provides `DATABASE_URL`

3. **Deploy**
   - Railway automatically deploys on git push
   - Uses `nixpacks.toml` configuration
   - Gunicorn serves the application

## 📊 Database Schema

### Tables
- `users` - User accounts and profiles
- `user_priorities` - Magic 10 priority settings
- `compatibility_matrix` - Pre-calculated compatibility scores
- `birth_data` - Birth information for Human Design
- `human_design_data` - Calculated Human Design charts
- `admin_action_log` - Admin action audit trail
- `email_notifications` - Email delivery tracking
- `user_sessions` - Session management

### Key Features
- INTEGER primary keys (Railway-compatible)
- TEXT fields for JSON data (no JSONB dependency)
- Proper foreign key relationships
- Optimized indexes for performance

## 🔌 API Endpoints

### Authentication
- `POST /api/auth/register` - User registration
- `POST /api/auth/login` - User login
- `POST /api/auth/logout` - User logout
- `GET /api/auth/me` - Get current user

### Magic 10 Matching
- `GET /api/priorities` - Get user priorities
- `PUT /api/priorities` - Update user priorities
- `POST /api/compatibility/calculate` - Calculate compatibility
- `GET /api/matches` - Get user matches

### Human Design
- `GET /api/birth-data` - Get birth data
- `POST /api/birth-data` - Save birth data
- `POST /api/human-design/calculate` - Calculate chart
- `GET /api/human-design` - Get chart data

### Admin Console
- `GET /api/admin/users` - List all users
- `PUT /api/admin/users/:id/status` - Update user status
- `DELETE /api/admin/users/:id` - Delete user
- `GET /api/admin/stats` - System statistics
- `POST /api/admin/compatibility/recalculate` - Recalculate all compatibility
- `GET /api/admin/logs` - Admin action logs

### System
- `GET /api/health` - Health check
- `GET /api/debug/env` - Environment debug (remove in production)

## 🧮 Magic 10 Algorithm

### Dimensions
1. **Love** - Romantic connection and affection
2. **Intimacy** - Physical and emotional closeness
3. **Communication** - Expression and understanding
4. **Friendship** - Companionship and fun
5. **Collaboration** - Working together and teamwork
6. **Lifestyle** - Daily habits and life choices
7. **Decisions** - Decision-making and planning
8. **Support** - Emotional and practical support
9. **Growth** - Personal development and learning
10. **Space** - Independence and personal time

### Calculation
- Each user sets priorities (1-10) for each dimension
- Compatibility calculated based on priority alignment
- Weighted scoring considers mutual importance
- Bonuses for high mutual priorities
- Penalties for major mismatches
- Final score: 0-100 compatibility percentage

## 🔧 Local Development

### Setup
```bash
# Clone repository
git clone <repository-url>
cd glow-railway-final

# Install dependencies
pip install -r requirements.txt

# Set environment variables
export SECRET_KEY="dev-secret-key"
export DATABASE_URL="sqlite:///glow_dev.db"

# Run application
python app.py
```

### Testing
```bash
# Health check
curl http://localhost:5000/api/health

# Register user
curl -X POST http://localhost:5000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"password123","first_name":"Test"}'

# Login
curl -X POST http://localhost:5000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"password123"}'
```

## 🛡️ Security Features

- **Password Hashing** - Werkzeug secure password hashing
- **Session Management** - Secure token-based sessions
- **Input Validation** - Comprehensive request validation
- **CORS Protection** - Configurable origin restrictions
- **Error Handling** - Safe error responses (no sensitive data)
- **Admin Logging** - Complete audit trail for admin actions

## 📈 Performance Optimizations

- **Single-File Architecture** - Reduced import overhead
- **Lazy Database Initialization** - Faster startup times
- **Pre-calculated Compatibility** - Matrix storage for quick lookups
- **Indexed Database Fields** - Optimized query performance
- **Minimal Dependencies** - Reduced memory footprint
- **Connection Pooling** - PostgreSQL connection optimization

## 🔍 Monitoring and Debugging

### Health Check
```bash
curl https://your-app.railway.app/api/health
```

### Environment Debug
```bash
curl https://your-app.railway.app/api/debug/env
```

### Admin Statistics
```bash
curl -H "Authorization: Bearer <token>" \
  https://your-app.railway.app/api/admin/stats
```

## 🚀 Production Considerations

### Required for Production
1. **Remove debug endpoints** - Delete `/api/debug/env`
2. **Set strong SECRET_KEY** - Use secure random string
3. **Configure external APIs** - Mailgun, Human Design API
4. **Set up monitoring** - Health check endpoints
5. **Configure CORS** - Restrict to production domains

### Optional Enhancements
1. **Rate Limiting** - Add request rate limiting
2. **Caching** - Redis for session/API caching
3. **File Storage** - Cloud storage for user photos
4. **Background Jobs** - Async email sending
5. **Analytics** - User behavior tracking

## 📞 Support

For deployment issues or questions:
1. Check Railway logs in dashboard
2. Verify environment variables
3. Test health endpoint
4. Review admin statistics

## 🔄 Version History

- **v1.0.0** - Initial Railway-optimized release
  - Single-file architecture
  - Complete Magic 10 matching
  - Human Design integration
  - Admin console
  - Email notifications
  - Railway deployment ready

# Railway Auto-Deploy Test
