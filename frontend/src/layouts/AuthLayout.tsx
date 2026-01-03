import React from 'react'
import { Card } from 'antd'

interface AuthLayoutProps {
  children: React.ReactNode
}

const AuthLayout: React.FC<AuthLayoutProps> = ({ children }) => {
  return (
    <div className="min-h-screen bg-gradient-to-br from-primary-500 to-primary-700 flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        {/* Logo */}
        <div className="text-center mb-8">
          <h1 className="text-3xl font-heading font-bold text-white mb-2">
            Alphha DMS
          </h1>
          <p className="text-primary-100">
            Enterprise Document Management System
          </p>
        </div>

        {/* Card */}
        <Card className="shadow-xl">
          {children}
        </Card>

        {/* Footer */}
        <p className="text-center text-primary-200 text-sm mt-6">
          &copy; {new Date().getFullYear()} Alphha. All rights reserved.
        </p>
      </div>
    </div>
  )
}

export default AuthLayout
