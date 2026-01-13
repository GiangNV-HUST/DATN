-- Add is_active column to subscriptions table if it doesn't exist
ALTER TABLE public.subscriptions 
ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE;

-- Create index for is_active if not exists
CREATE INDEX IF NOT EXISTS idx_public_subscriptions_active ON public.subscriptions(is_active);
