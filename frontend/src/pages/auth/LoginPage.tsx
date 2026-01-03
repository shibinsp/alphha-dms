import React, { useState } from 'react'
import { Form, Input, Button, message, Divider } from 'antd'
import { UserOutlined, LockOutlined, SafetyOutlined } from '@ant-design/icons'
import { useAuthStore } from '@/store/authStore'
import { authService } from '@/services/authService'

interface LoginFormValues {
  email: string
  password: string
  mfa_code?: string
}

const LoginPage: React.FC = () => {
  const [loading, setLoading] = useState(false)
  const [requiresMFA, setRequiresMFA] = useState(false)
  const [form] = Form.useForm()
  const login = useAuthStore((state) => state.login)

  const handleSubmit = async (values: LoginFormValues) => {
    setLoading(true)
    try {
      const { user, tokens } = await authService.login({
        email: values.email,
        password: values.password,
        mfa_code: values.mfa_code,
      })

      login(user, tokens)
      message.success('Login successful!')
    } catch (error: unknown) {
      const err = error as { response?: { data?: { detail?: string | Array<{msg: string}> } } }
      const detail = err.response?.data?.detail

      // Handle validation errors (array format)
      let errorMessage = 'Login failed'
      if (Array.isArray(detail)) {
        errorMessage = detail.map(e => e.msg).join(', ')
      } else if (typeof detail === 'string') {
        errorMessage = detail
      }

      if (errorMessage === 'MFA code required') {
        setRequiresMFA(true)
        message.info('Please enter your MFA code')
      } else {
        message.error(errorMessage)
      }
    } finally {
      setLoading(false)
    }
  }

  return (
    <div>
      <h2 className="text-2xl font-heading font-semibold text-center mb-6">
        Welcome Back
      </h2>

      <Form
        form={form}
        layout="vertical"
        onFinish={handleSubmit}
        size="large"
      >
        <Form.Item
          name="email"
          rules={[
            { required: true, message: 'Please enter your email' },
            { type: 'email', message: 'Please enter a valid email' },
          ]}
        >
          <Input
            prefix={<UserOutlined className="text-gray-400" />}
            placeholder="Email address"
            autoComplete="email"
          />
        </Form.Item>

        <Form.Item
          name="password"
          rules={[{ required: true, message: 'Please enter your password' }]}
        >
          <Input.Password
            prefix={<LockOutlined className="text-gray-400" />}
            placeholder="Password"
            autoComplete="current-password"
          />
        </Form.Item>

        {requiresMFA && (
          <Form.Item
            name="mfa_code"
            rules={[
              { required: true, message: 'Please enter your MFA code' },
              { len: 6, message: 'MFA code must be 6 digits' },
            ]}
          >
            <Input
              prefix={<SafetyOutlined className="text-gray-400" />}
              placeholder="Enter 6-digit code"
              maxLength={6}
            />
          </Form.Item>
        )}

        <Form.Item className="mb-0">
          <Button
            type="primary"
            htmlType="submit"
            loading={loading}
            block
          >
            Sign In
          </Button>
        </Form.Item>
      </Form>

      <Divider plain className="text-gray-400">
        <span className="text-sm">Secure access</span>
      </Divider>

      <p className="text-center text-gray-500 text-sm">
        Protected by enterprise-grade security with AES-256 encryption and
        immutable audit trails.
      </p>
    </div>
  )
}

export default LoginPage
