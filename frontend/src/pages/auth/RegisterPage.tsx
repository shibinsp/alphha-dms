import React, { useState } from 'react'
import { Form, Input, Button, message } from 'antd'
import { UserOutlined, LockOutlined, MailOutlined } from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'
import api from '@/services/api'

const RegisterPage: React.FC = () => {
  const [loading, setLoading] = useState(false)
  const [form] = Form.useForm()
  const navigate = useNavigate()

  const handleSubmit = async (values: any) => {
    setLoading(true)
    try {
      await api.post('/auth/register', {
        email: values.email,
        password: values.password,
        full_name: values.full_name
      })
      message.success('Account created! Please sign in.')
      navigate('/login')
    } catch (error: any) {
      const detail = error.response?.data?.detail
      message.error(typeof detail === 'string' ? detail : 'Registration failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div>
      <h2 className="text-2xl font-heading font-semibold text-center mb-6">
        Create Account
      </h2>

      <Form form={form} layout="vertical" onFinish={handleSubmit} size="large">
        <Form.Item
          name="full_name"
          rules={[{ required: true, message: 'Please enter your name' }]}
        >
          <Input
            prefix={<UserOutlined className="text-gray-400" />}
            placeholder="Full name"
          />
        </Form.Item>

        <Form.Item
          name="email"
          rules={[
            { required: true, message: 'Please enter your email' },
            { type: 'email', message: 'Please enter a valid email' }
          ]}
        >
          <Input
            prefix={<MailOutlined className="text-gray-400" />}
            placeholder="Email address"
          />
        </Form.Item>

        <Form.Item
          name="password"
          rules={[
            { required: true, message: 'Please enter a password' },
            { min: 8, message: 'Password must be at least 8 characters' }
          ]}
        >
          <Input.Password
            prefix={<LockOutlined className="text-gray-400" />}
            placeholder="Password"
          />
        </Form.Item>

        <Form.Item
          name="confirm_password"
          dependencies={['password']}
          rules={[
            { required: true, message: 'Please confirm your password' },
            ({ getFieldValue }) => ({
              validator(_, value) {
                if (!value || getFieldValue('password') === value) {
                  return Promise.resolve()
                }
                return Promise.reject(new Error('Passwords do not match'))
              }
            })
          ]}
        >
          <Input.Password
            prefix={<LockOutlined className="text-gray-400" />}
            placeholder="Confirm password"
          />
        </Form.Item>

        <Form.Item className="mb-4">
          <Button type="primary" htmlType="submit" loading={loading} block>
            Create Account
          </Button>
        </Form.Item>
      </Form>

      <p className="text-center text-sm">
        Already have an account?{' '}
        <Button type="link" className="p-0" onClick={() => navigate('/login')}>
          Sign In
        </Button>
      </p>
    </div>
  )
}

export default RegisterPage
