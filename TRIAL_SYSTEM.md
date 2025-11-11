# Trial System Documentation

## Overview

The Sprache Motivator bot now includes a 10-day free trial system. New users must activate their trial to access the translator and trainer features. After the trial expires, users are prompted to subscribe for €5/month.

## User Flow

### 1. Initial Registration
1. User sends `/start` command
2. User selects interface language (Ukrainian or Russian)
3. Admin approves the user (or user is auto-approved if they're an admin)
4. User sees welcome message with trial activation button

### 2. Trial Activation
1. User clicks "🎁 Start 10-day free trial" button
2. Trial activation timestamp is recorded in Berlin timezone
3. User gets confirmation message showing days remaining
4. Main menu appears with full access to all features

### 3. During Trial Period
- User has full access to translator and trainer modes
- Settings page shows trial status and days remaining
- All times are displayed in Berlin timezone

### 4. Trial Expiration
- After exactly 10 days (Berlin timezone), trial expires
- User sees subscription offer when trying to access features
- Message includes:
  - €5/month subscription price
  - Stripe payment link
  - Admin contact for support

## Configuration

### Environment Variables

Add these to your `.env` file:

```env
# Stripe payment link for subscription
STRIPE_PAYMENT_LINK=https://buy.stripe.com/your_payment_link_here

# Admin contact for support
ADMIN_CONTACT=@your_telegram_username
```

### Setting Up Stripe Payment Link

1. Create a Stripe account at https://stripe.com
2. Set up a product for "Sprache Motivator Monthly Subscription" at €5/month
3. Create a payment link for this product
4. Add the payment link URL to `STRIPE_PAYMENT_LINK` in `.env`

## Database Schema

### Trial Fields in User Collection

```javascript
{
  "trial_activated": Boolean,          // Has user activated their trial?
  "trial_activation_date": DateTime,   // When was trial activated (UTC)
  "subscription_active": Boolean       // Does user have paid subscription?
}
```

## Admin Access

Administrators (users listed in `ADMIN_IDS`) automatically get:
- Trial activated on first use
- Subscription marked as active
- No expiration (unlimited access)

## Timezone Details

All trial calculations use **Berlin timezone (Europe/Berlin)**:
- Trial activation timestamp
- Trial expiration calculation (activation + 10 days)
- Days remaining display
- Trainer scheduling times

This is displayed to users in:
- Settings menu
- Trainer settings
- Trial status messages

## Access Control Logic

### Translator Mode
**Before activation:**
- Shows: "⚠️ Please activate free 10-day trial to use this feature"
- Directs user to `/start`

**After expiration:**
- Shows: "⏰ Your 10-day trial has expired!"
- Displays subscription offer with payment link
- Shows admin contact

### Trainer Mode
Same access control as translator mode.

## Testing

Run the trial system tests:

```bash
# Unit tests
python test_trial_logic.py

# Integration tests
python test_trial_flow_integration.py
```

## Localization

Trial messages are available in:
- **Ukrainian** (`uk`)
- **Russian** (`ru`)

Localization keys:
- `welcome_with_trial` - Welcome message with trial info
- `btn_activate_trial` - Trial activation button
- `trial_activated` - Confirmation message
- `trial_not_activated` - Access blocked message
- `trial_expired` - Expiration with subscription offer
- `trial_status` - Status display in settings

## Migration Notes

### For Existing Users

When this feature is deployed:
- Existing users will have `trial_activated = False`
- They will need to activate trial to continue using the bot
- Admins are auto-activated when they use `/start`

### Database Migration

No manual migration needed. The fields are added with default values:
- `trial_activated`: `False` (except admins: `True`)
- `trial_activation_date`: `None` (except admins: current time)
- `subscription_active`: `False` (except admins: `True`)

## Troubleshooting

### Users can't access features after activation
- Check that `trial_activated = True` in database
- Verify `trial_activation_date` is set
- Ensure less than 10 days have passed (Berlin timezone)

### Payment link not showing
- Verify `STRIPE_PAYMENT_LINK` is set in `.env`
- Check that trial has actually expired
- Look for payment link in trial expired message

### Timezone confusion
- All times are in Berlin timezone
- Trial is exactly 10 days from activation (240 hours)
- Use Berlin time when communicating with users

## Future Enhancements

Potential improvements:
- Email/webhook notification when trial expires
- Automatic subscription status sync with Stripe
- Grace period after trial expiration
- Trial extension for specific users
- Analytics dashboard for trial conversion rate
