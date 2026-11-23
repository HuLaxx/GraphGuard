import type { ReactNode } from 'react';

type PageIntroProps = {
    title: string;
    lede: ReactNode;
    aside?: ReactNode;
};

/** Opening block shared by the inner pages: left-aligned title, serif lede, optional aside. */
export function PageIntro({ title, lede, aside }: PageIntroProps) {
    return (
        <section className="gg-intro">
            <div className="gg-wrap gg-intro__grid">
                <div>
                    <h1 className="gg-intro__title">{title}</h1>
                    <p className="gg-intro__lede">{lede}</p>
                </div>
                {aside ? <div className="gg-intro__aside">{aside}</div> : null}
            </div>
        </section>
    );
}
