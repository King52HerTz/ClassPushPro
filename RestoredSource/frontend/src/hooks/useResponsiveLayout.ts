import { useState, useEffect } from 'react';
import { Grid } from 'antd';

const { useBreakpoint } = Grid;

export const useResponsiveLayout = () => {
    const screens = useBreakpoint();
    const [isMobile, setIsMobile] = useState(false);

    useEffect(() => {
        // xs: <576px
        if (screens.xs) {
            setIsMobile(true);
        } else {
            setIsMobile(false);
        }
    }, [screens]);

    return { isMobile };
};
