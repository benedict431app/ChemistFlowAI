# ChemistFlow - Pharmacy Management System

A comprehensive Python-based pharmacy management system with AI chat assistant, built with Streamlit and PostgreSQL.

## Features

### Multi-Role Authentication
- **Admin (Chemist Owner)**: Full system access with customizable pharmacy display name
- **Employees**: Must be approved by admin before accessing the system
- **Customers**: Can view their account status, credit history, and payments (read-only)

### Core Modules

#### 1. Inventory Management
- Manual product entry with full details (name, category, price, stock, supplier)
- Barcode scanning using mobile phone or computer camera
- Automatic barcode generation for products
- Low stock alerts
- Real-time search functionality

#### 2. Point of Sale (POS)
- Multi-payment mode support: Cash, Credit, M-Pesa, Card
- Shopping cart with real-time calculations
- Receipt generation (PDF format)
- Credit limit enforcement
- Offline sales capability with automatic sync when online

#### 3. Customer Relationship Management (CRM)
- Schedule follow-ups with customers
- Track interactions (calls, visits, emails, SMS)
- Follow-up calendar with today's tasks and upcoming reminders
- Complete interaction history

#### 4. Complaints & Support
- Customers, employees, and users can submit complaints
- Admin can respond through chat interface
- Status tracking (pending, in progress, resolved)
- Notification system for new complaints

#### 5. AI Chat Assistant
- Powered by Cohere API
- Pharmacy-specific knowledge
- Medicine information and usage guidance
- 24/7 customer support

#### 6. Reports & Analytics
- Sales summary reports
- Revenue by payment mode
- Top products analysis
- Customer credit reports
- Sales trend visualization

### Additional Features

- **Password Reset**: Forgot password functionality for all users
- **Notifications**: Real-time system notifications for admins
- **Mobile-Responsive**: Optimized for mobile devices
- **Kenyan Currency**: KES formatting throughout the system
- **PostgreSQL Database**: Reliable data storage with relationships
- **Offline Mode**: Continue sales when internet is unavailable

## Default Credentials

**Admin Account:**
- Username: `admin`
- Password: `admin123`

## System Requirements

- Python 3.11+
- PostgreSQL database
- Camera access for barcode scanning
- Internet connection for AI assistant (optional for offline sales)

## Installation

1. All dependencies are pre-installed
2. Database is automatically initialized on first run
3. Default admin account is created automatically

## Usage Guide

### For Admin (Chemist Owner)

1. **Login** with default credentials
2. **Settings**: Update pharmacy display name (appears to all employees)
3. **Employee Approvals**: Approve or reject employee registrations (password-protected)
4. **Inventory**: Manage products, scan barcodes, add new items
5. **Sales**: Process transactions with multiple payment modes
6. **Customers**: Manage customer accounts and credit limits
7. **CRM**: Schedule follow-ups and track interactions
8. **Complaints**: Respond to complaints from customers and employees
9. **Reports**: View analytics and generate reports
10. **Notifications**: Check system notifications
11. **AI Assistant**: Get help with pharmacy operations

### For Employees

1. **Register** and wait for admin approval
2. **Login** after approval
3. See pharmacy name (set by admin) at top
4. **Sales**: Process customer transactions
5. **Inventory**: View products and scan barcodes
6. **Customers**: View and add customers
7. **Support**: Submit complaints or issues
8. **AI Assistant**: Get pharmacy assistance

### For Customers

1. **Register** as customer (approved automatically)
2. **Login** to customer portal
3. **My Account**: View credit status (read-only)
4. **Purchase History**: View all purchases
5. **Payments**: View payment history and outstanding credit
6. **Support**: Submit complaints and chat with admin
7. **AI Assistant**: Ask pharmacy questions

## Payment Modes

- **Cash**: Immediate payment
- **Credit**: Requires customer with credit limit
- **M-Pesa**: Mobile money with transaction ID
- **Card**: Card payment

## Offline Sales

1. Enable "Offline Mode" in sales module
2. Process sales normally
3. Sales are saved locally
4. Automatic sync when connection is restored

## Barcode Scanning

1. Go to Inventory > Barcode Scanner
2. Allow camera access
3. Point camera at barcode
4. System will detect and display product
5. Add to cart for quick sales

## Credit Management

- Admin sets credit limit per customer
- System enforces limits during sales
- Customers can view outstanding credit
- Payment recording updates credit balance

## Security Features

- Password hashing with bcrypt
- Session management
- Role-based access control
- Password-protected admin approvals
- Reset token expiry (1 hour)

## Technical Stack

- **Frontend**: Streamlit
- **Backend**: Python 3.11
- **Database**: PostgreSQL
- **ORM**: SQLAlchemy
- **AI**: Cohere API
- **Barcode**: pyzbar, opencv-python
- **PDF**: ReportLab
- **Authentication**: bcrypt

## Environment Variables

- `DATABASE_URL`: PostgreSQL connection string (auto-configured)
- `COHERE_API_KEY`: Cohere API key for AI assistant

## Support

For issues or questions, contact the pharmacy administrator or use the AI Assistant feature.

---

**ChemistFlow** - Your Complete Pharmacy Management Solution 💊
